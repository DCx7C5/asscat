import asyncio
from asyncio import (
    AbstractEventLoop,
    Server,
)

from typing import List, Optional

from asscat.streams import StdIOStream
from asscat.protocols import RevShellSession


class ListenerFactory:

    @classmethod
    async def create(cls, loop, manager) -> Server:

        server = await loop.create_server(
            protocol_factory=lambda: RevShellSession(loop=loop, manager=manager),
            host='127.0.0.1',
            port=8888,
            reuse_port=True,
            reuse_address=True,
            start_serving=True,
        )
        manager.listeners.append(server)
        return server


class AssCatManager:
    """Management class that provides all the resources"""
    def __init__(self):
        self._loop: AbstractEventLoop = asyncio.get_event_loop()
        self.stdio: Optional[StdIOStream] = None
        self.listeners: List[Server] = []
        self.sessions: List[RevShellSession] = []
        self.active_session: Optional[RevShellSession] = None

    async def start(self):
        listener = await ListenerFactory.create(self._loop, self)
        self.stdio = await StdIOStream.create(self._loop)
        async with listener:
            await listener.serve_forever()

    async def shutdown(self):
        await self.stdio.close()
        for session in self.sessions:
            await session.stream.close()
        for listener in self.listeners:
            listener.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


async def main():
    async with AssCatManager() as dcm:
        await dcm.start()


if __name__ == '__main__':
    try:
        asyncio.run(main=main())
    except KeyboardInterrupt:
        pass
