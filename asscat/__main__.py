import sys
import asyncio
from asyncio import (
    AbstractEventLoop,
    ReadTransport,
    WriteTransport,
    Server,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol, CancelledError, Event,
)

from asyncio.streams import FlowControlMixin  # noqa
from typing import List, Optional

from asscat.protocols import RevshellProtocol
from asscat.sessions import Session


class DCatManager:

    def __init__(self):
        self.loop: AbstractEventLoop = asyncio.get_event_loop()
        self.server: Optional[Server] = None
        self.stdin_reader: Optional[StreamReader] = None
        self._stdin_transport: Optional[ReadTransport] = None
        self.stdout_writer: Optional[StreamWriter] = None
        self._stdout_transport: Optional[WriteTransport] = None
        self.sessions: List[Session] = []
        self.stdio_ready = Event()
        self.session_is_ready = Event()

        self.loop.set_exception_handler(self.handle_exception)

    async def create_stdio_reader_writer(self):
        loop = self.loop
        reader = asyncio.StreamReader()
        r_transport, _ = await loop.connect_read_pipe(
            lambda: StreamReaderProtocol(reader, loop=loop), sys.stdin.buffer)
        self.stdin_reader = reader
        w_transport, w_protocol = await loop.connect_write_pipe(FlowControlMixin, sys.stdout.buffer)
        writer = StreamWriter(w_transport, w_protocol, reader, loop)
        self.stdin_reader, self.stdout_writer = reader, writer
        self._stdin_transport, self._stdout_transport = r_transport, w_transport
        self.stdio_ready.set()

    async def create_listener(self):
        self.server = await self.loop.create_server(
            protocol_factory=lambda: RevshellProtocol(loop=self.loop, manager=self),
            host='127.0.0.1',
            port=8888,
            reuse_port=True,
            reuse_address=True,
        )
        print(self.server)

    async def start(self):
        await self.create_stdio_reader_writer()
        await self.create_listener()
        try:
            async with self.server:
                await self.server.serve_forever()
        except Exception as exc:
            await self.handle_exception(exc)

    async def handle_exception(self, exc):
        print(f'Exception: {exc}')
        if isinstance(exc, KeyboardInterrupt):
            self.shutdown()
        elif isinstance(exc, CancelledError):
            self.shutdown()

    def shutdown(self):
        self.server.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.handle_exception(exc_type)


async def main():
    async with DCatManager() as dcm:
        await dcm.start()


if __name__ == '__main__':
    asyncio.run(main=main())
