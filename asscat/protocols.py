import itertools
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamReaderProtocol,
    Task,
    SubprocessProtocol,
)
from asyncio.streams import FlowControlMixin  # noqa
from typing import Optional

from asscat.streams import TCPStream


class BaseSession(StreamReaderProtocol):
    conn_counter = itertools.count()


class RevShellSession(BaseSession):

    def __init__(self, loop: AbstractEventLoop, manager):
        self._loop = loop
        super().__init__(
            stream_reader=StreamReader(loop=self._loop),
            client_connected_cb=self._connection_made_cb,
            loop=self._loop,
        )
        self.manager = manager
        self.stream: Optional[TCPStream] = None
        self._transport = None
        self.connection_closed: bool = True
        self._connection_closed: bool = True
        self._conn_handler_task: Optional[Task] = None
        self._data_handler_task: Optional[Task] = None
        self._send_cmd_task: Optional[Task] = None
        self._session_id: int = next(BaseSession.conn_counter)

    def connection_made(self, transport):
        self._transport = transport
        super().connection_made(transport)
        self.connection_closed = False
        self._send_cmd_task = self._loop.create_task(self.send_cmd())

    def data_received(self, data: bytes):
        super().data_received(data)
        self._data_handler_task = self._loop.create_task(self._handle_data())
        if self._send_cmd_task.done():
            self._send_cmd_task = self._loop.create_task(self.send_cmd())

    def connection_lost(self, exc: Exception):
        super().connection_lost(exc)
        self.connection_closed = self._connection_closed = True
        try:
            self.manager.sessions.remove(self)
        except ValueError:
            pass

    async def _handle_data(self):
        data = await self.stream.read()
        await self.manager.stdio.write(data)

    async def send_cmd(self):
        cmd = await self.manager.stdio.readline()
        await self.manager.active_session.stream.write(cmd)

    def _connection_made_cb(self, reader, writer):
        self.stream = TCPStream.create(self._loop, reader, writer)
        self.manager.sessions.append(self)
        if self.manager.active_session is None:
            self.manager.active_session = self
        print(f'Connection from {self._transport.get_extra_info("peername")}', self._session_id)


class LocalSession(SubprocessProtocol):
    pass
