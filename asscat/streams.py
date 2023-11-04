import sys
import traceback
from abc import ABC
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol, sleep,
)
from asyncio.streams import FlowControlMixin  # noqa
from typing import Optional

from asscat.exceptions import BufferSizeLimitError

DEFAULT_LIMIT = 2 ** 16


class AssCatReader:

    __slots__ = ('_loop', '_limit')
    _traceback = None

    def __init__(self, loop: AbstractEventLoop, limit: int = None):
        self._loop: AbstractEventLoop = loop
        if limit is None:
            self._limit = DEFAULT_LIMIT
        elif limit <= 0:
            raise BufferSizeLimitError(limit)


class AssCatWriter:
    """Transport wrapper"""
    __slots__ = ('_transport', '_protocol', '_reader', '_loop',
                 '_complete_fut',)

    def __init__(
            self,
            transport,
            protocol,
            reader: StreamReader,
            loop: AbstractEventLoop,
    ):
        self._loop: AbstractEventLoop = loop
        self._transport = transport

        self._protocol = protocol
        self._reader: StreamReader = reader
        self._complete_fut = self._loop.create_future()
        self._complete_fut.set_result(None)

    @property
    def transport(self):
        return self._transport

    @property
    def protocol(self):
        return self._protocol

    @property
    def reader(self):
        return self._reader

    def write(self, data):
        self._transport.write(data)

    def writelines(self, data):
        self._transport.writelines(data)

    def write_eof(self):
        return self._transport.write_eof()

    def can_write_eof(self):
        return self._transport.can_write_eof()

    def close(self):
        return self._transport.close()

    def is_closing(self):
        return self._transport.is_closing()

    async def wait_closed(self):
        await self._protocol._get_close_waiter(self)

    def get_extra_info(self, name, default=None):
        return self._transport.get_extra_info(name, default)

    async def _handle_exception(self, exc: Exception):
        traceback.print_exc()

    async def _check_for_exception(self):
        """Checks for exception and sends it to exc handler"""
        exc = self._reader.exception()
        if isinstance(exc, Exception):
            await self._handle_exception(exc)

    async def flush(self) -> None:
        """Flush the stdout write buffer"""
        if isinstance(self._reader, StreamReader):
            await self._check_for_exception()
        if self._transport.is_closing():
            await sleep(.1)
        await self._protocol._drain_helper()  # noqa: pm

    async def start_tls(self, sslcontext, *,
                        server_hostname=None,
                        ssl_handshake_timeout=None):
        """Upgrade an existing stream-based connection to TLS."""
        server_side = self._protocol._client_connected_cb is not None  # noqa: pm
        protocol = self._protocol
        await self.flush()
        new_transport = await self._loop.start_tls(
            self._transport, protocol, sslcontext,
            server_side=server_side, server_hostname=server_hostname,
            ssl_handshake_timeout=ssl_handshake_timeout)
        self._transport = new_transport
        protocol._replace_writer(self)  # noqa: pm

    def __del__(self):
        if not self._transport.is_closing():
            self.close()


class StdIOReader:
    _source_traceback = None
    __slots__ = ('_loop', )

    def __init__(self, loop: AbstractEventLoop):
        self._loop: AbstractEventLoop = loop



class Stream(ABC):
    """
    Abstract class that wraps a reader, writer
    or both to represent a connection
    """
    __slots__ = ('_loop', '_reader', '_writer')

    def __init__(self):
        self._loop: Optional[AbstractEventLoop] = None
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

    async def read(self) -> bytes:
        return await self._reader.read(8192)

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()


class StdIOStream(Stream):

    def __init__(self, loop: AbstractEventLoop):
        super().__init__()
        self._loop = loop

    async def _create_reader(self):
        self._reader = StreamReader()
        transport, _ = await self._loop.connect_read_pipe(
            protocol_factory=lambda: StreamReaderProtocol(self._reader, loop=self._loop),
            pipe=sys.stdin
        )

    async def _create_writer(self):
        transport, protocol = await self._loop.connect_write_pipe(
            protocol_factory=FlowControlMixin,
            pipe=sys.stdout
        )
        self._writer = StreamWriter(
            transport=transport,
            protocol=protocol,
            reader=self._reader,
            loop=self._loop
        )

    @classmethod
    async def create(cls, loop: AbstractEventLoop):
        self = cls(loop)
        await self._create_reader()
        await self._create_writer()
        return self


class SocketStream(Stream):

    def __init__(self, loop: AbstractEventLoop):
        super().__init__()
        self._loop = loop

    @classmethod
    def create(cls, loop: AbstractEventLoop, reader: StreamReader, writer: StreamWriter):
        self = cls(loop)
        self._reader = reader
        self._writer = writer
        return self
