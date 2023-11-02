import sys
from abc import ABC
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol,
)
from asyncio.streams import FlowControlMixin  # noqa
from typing import Optional


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
