import itertools
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol, Task,
)
from asyncio.streams import FlowControlMixin # noqa
from typing import Optional


class BaseRevShellProtocol(StreamReaderProtocol): ...


class RevShellSession(BaseRevShellProtocol):
    conn_counter = itertools.count()

    def __init__(self, loop: AbstractEventLoop, manager):
        self.loop = loop
        super().__init__(
            stream_reader=StreamReader(loop=self.loop),
            client_connected_cb=self._connection_made_cb,
            loop=self.loop,
        )
        self.manager = manager
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self.transport = None
        self.connection_closed: bool = True
        self._connection_closed: bool = True
        self._conn_handler_task: Optional[Task] = None
        self._data_handler_task: Optional[Task] = None
        self._send_cmd_task: Optional[Task] = None

    def connection_made(self, transport):
        super().connection_made(transport)
        self.transport = transport
        self.manager.sessions.append(self)
        self.connection_closed = False
        print(f'connection made from {transport.get_extra_info("peername")}')
        self._send_cmd_task = self.loop.create_task(self._send_cmd())

    def data_received(self, data: bytes):
        super().data_received(data)
        self._data_handler_task = self.loop.create_task(self._handle_data())
        if self._send_cmd_task.done():
            self._send_cmd_task = self.loop.create_task(self._send_cmd())

    def connection_lost(self, exc):
        super().connection_lost(exc)
        self.connection_closed = self._connection_closed = True
        try:
            self.manager.sessions.remove(self)
        except ValueError:
            pass

    async def _handle_data(self):
        data = await self._reader.read(8192)
        self.manager.stdout_writer.write(data)
        await self.manager.stdout_writer.drain()

    async def _send_cmd(self):
        cmd = await self.manager.stdin_reader.readline()
        self._writer.write(cmd)
        await self._writer.drain()

    def _connection_made_cb(self, reader, writer):
        self._reader = self.reader = reader
        self._writer = self.writer = writer
