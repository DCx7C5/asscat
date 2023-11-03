import asyncio
import itertools
from abc import ABC
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamReaderProtocol,
    Task,
    SubprocessProtocol,
)
from asyncio.streams import FlowControlMixin  # noqa
from typing import Optional

from asscat.commands import Command
from asscat.streams import SocketStream


class BaseSession(ABC):
    conn_counter = itertools.count()


class BaseRevShellSession(BaseSession, StreamReaderProtocol): ...


class RevShellSession(BaseRevShellSession):

    def __init__(self, loop: AbstractEventLoop, manager):
        self._loop = loop
        super().__init__(
            stream_reader=StreamReader(loop=self._loop),
            client_connected_cb=self._connection_made_cb,
            loop=self._loop,
        )
        self.manager = manager
        self.stream: Optional[SocketStream] = None
        self._transport = None
        self._connection_closed: bool = True
        self._conn_handler_task: Optional[Task] = None
        self._data_handler_task: Optional[Task] = None
        self._send_cmd_task: Optional[Task] = None
        self._session_id: int = next(BaseSession.conn_counter)

    def connection_made(self, transport):
        self._transport = transport
        super().connection_made(transport)
        self._connection_closed = False
        if self.manager.active_session == self:
            self._send_cmd_task = self._loop.create_task(self.send_cmd())

    def data_received(self, data: bytes):
        super().data_received(data)
        self._data_handler_task = self._loop.create_task(self._handle_data())
        if self._send_cmd_task and self._send_cmd_task.done():
            self._send_cmd_task = self._loop.create_task(self.send_cmd())

    def connection_lost(self, exc: Exception):
        super().connection_lost(exc)
        self._connection_closed = True
        try:
            self.manager.sessions.remove(self)
        except ValueError:
            pass

    async def _handle_data(self):
        data = await self.manager.active_session.stream.read()
        await self.manager.stdio.write(data)
        self._data_handler_task.done()

    async def send_cmd(self):
        rawcmd = await self.manager.stdio.readline()
        cmd = await Command.parse(manager=self.manager, raw_cmd=rawcmd)
        if cmd is None:
            self._send_cmd_task.done()
            self._send_cmd_task = await self._loop.create_task(self.send_cmd())
        else:
            await self.manager.active_session.stream.write(cmd)
            self._send_cmd_task.done()

    def _connection_made_cb(self, reader, writer):
        self.stream = SocketStream.create(self._loop, reader, writer)
        self.manager.sessions.append(self)
        if self.manager.active_session is None:
            self.manager.active_session = self
        print(f'Connection from {self._transport.get_extra_info("peername")}', self._session_id)


class LocalSession(SubprocessProtocol):
    pass
