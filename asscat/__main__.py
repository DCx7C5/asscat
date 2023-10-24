import sys
import asyncio
from asyncio import (
    AbstractEventLoop,
    ReadTransport,
    WriteTransport,
    Server,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol,
    CancelledError,
)

from asyncio.streams import FlowControlMixin  # noqa
from typing import List, Optional

from asscat.protocols import RevShellSession
from asscat.sessions import Session


class AssCatManager:

    def __init__(self):
        self.loop: AbstractEventLoop = asyncio.get_event_loop()
        self.server: Optional[Server] = None
        self.stdin_reader: Optional[StreamReader] = None
        self.stdin_transport: Optional[ReadTransport] = None
        self.stdin_protocol = None
        self.stdout_writer: Optional[StreamWriter] = None
        self.stdout_transport: Optional[WriteTransport] = None
        self.stdout_protocol = None
        self.sessions: List[Session] = []

    async def start(self):
        loop = self.loop

        # Create TCP Socket Server
        self.server = await loop.create_server(
            protocol_factory=lambda: RevShellSession(loop=loop, manager=self),
            host='127.0.0.1',
            port=8888,
            reuse_port=True,
            reuse_address=True,
            start_serving=True,
        )

        # Create StdIn Reader, Proto, Transport
        self.stdin_reader = asyncio.StreamReader()
        self.stdin_protocol = lambda: StreamReaderProtocol(self.stdin_reader, loop=loop)
        self.stdin_transport, _ = await loop.connect_read_pipe(
            protocol_factory=self.stdin_protocol,
            pipe=sys.stdin
        )

        # Create StdOut Writer, Proto, Transport
        self.stdout_transport, self.stdout_protocol = await loop.connect_write_pipe(
            protocol_factory=FlowControlMixin,
            pipe=sys.stdout
        )
        self.stdout_writer = StreamWriter(
            transport=self.stdout_transport,
            protocol=self.stdout_protocol,
            reader=self.stdin_reader,
            loop=loop
        )

        try:
            async with self.server:
                await self.server.serve_forever()
        except Exception as exc:
            await self.handle_exception(exc, '')

    async def handle_exception(self, exc, msg):
        print(f'Exception: {exc}')
        if msg:
            print(f'MSG: ', msg)
        if isinstance(exc, KeyboardInterrupt):
            self.shutdown()
        elif isinstance(exc, CancelledError):
            self.shutdown()

    def shutdown(self):
        self.server.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.handle_exception(exc_type, exc_val)


async def main():
    async with AssCatManager() as dcm:
        await dcm.start()


if __name__ == '__main__':
    asyncio.run(main=main())
