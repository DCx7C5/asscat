from __future__ import annotations
import itertools

from asyncio import (
    AbstractEventLoop,
    Protocol,
    Transport,
    StreamReader,
    StreamWriter,
)
from asyncio.streams import FlowControlMixin  # noqa

from typing import Optional


class AssCatProtocol(FlowControlMixin, Protocol):
    """
    State machine of calls:

      start -> INCM -> OUTCM-> SOCM [-> INDR] [-> ] [-> EOF?] CL -> end

    * INCM: stdin_connection_made()
    * OUTCM: stdout_connection_made()
    * SOCM: socket_connection_made()
    * INDR: stdin_data_received()
    * SODR: socket_data_received()
    * EOF: eof_received()
    * CL: connection_lost()
    """
    conn_counter = itertools.count()

    def __init__(
            self,
            loop: AbstractEventLoop,
            manager,
            server_id,
    ):
        super().__init__(loop)
        self._loop: AbstractEventLoop = loop
        self._transport: Optional[Transport] = None
        self._stdout_transport = None
        self._stdin_transport = None
        self._session_id: int = next(AssCatProtocol.conn_counter)
        self._reader = None
        self._writer = None
        self._task = None
        self._over_ssl = False
        self._closed = self._loop.create_future()
        self._manager = manager
        self._read_blocked = False
        self._server_id = server_id

    @property
    def session_id(self):
        return self._session_id

    @property
    def reader(self):
        return self._reader

    @property
    def writer(self):
        return self._writer

    def _replace_writer(self, writer):
        transport = writer.transport
        self._stream_writer = writer
        self._transport = transport
        self._over_ssl = transport.get_extra_info('sslcontext') is not None

    def stdin_connection_made(self, transport) -> None:
        self._stdin_transport = transport

    def stdout_connection_made(self, transport) -> None:
        self._stdout_transport = transport

    def connection_made(self, transport: Transport) -> None:
        self._transport = transport
        self._reader = StreamReader(loop=self._loop)

        self._reader.set_transport(transport)

        self._over_ssl = transport.get_extra_info('sslcontext') is not None

        self._writer = StreamWriter(
            transport=transport,
            protocol=self,
            reader=self._reader,
            loop=self._loop)
        peerinfo = transport.get_extra_info('peername')
        self._manager.client_connected_cb(self, peerinfo)

    def connection_lost(self, exc: Exception, transport=None) -> None:
        if isinstance(transport, str):
            pass
        else:
            reader = self._reader
            if reader is not None:
                if exc is None:
                    reader.feed_eof()
                else:
                    reader.set_exception(exc)
            if not self._closed.done():
                if exc is None:
                    self._closed.set_result(None)
                else:
                    self._closed.set_exception(exc)
            super().connection_lost(exc)
            self._reader = None
            self._writer = None
            self._task = None
            self._transport = None

    def data_received(self, data: bytes) -> None:
        stdout = self._stdout_transport
        reader = self._reader
        if stdout is not None:
            stdout.write(data)
        if reader is not None:
            reader.feed_data(data)

    def stdin_data_received(self, data: bytes) -> None:
        self._transport.write(data)

    def eof_received(self):
        reader = self._reader
        if reader is not None:
            reader.feed_eof()
        if self._over_ssl:
            return False
        return True

    def _get_close_waiter(self):
        return self._closed

    def __del__(self):
        closed = self._closed
        if closed.done() and not closed.cancelled():
            closed.exception()

    def close(self):
        if self._reader:
            self._reader.close()
        if self._writer:
            self._writer.close()
        if self._stdout_transport:
            self._stdout_transport.pipe.close()
        if self._stdin_transport:
            self._stdin_transport.pipe.close()
