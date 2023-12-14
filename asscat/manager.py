from __future__ import annotations


import uvloop

from asyncio import AbstractEventLoop, Server, get_event_loop
from ssl import SSLContext
from typing import List, TypeVar, Dict, Optional, Tuple

from asscat.logger import setup_logger
from asscat.protocols import AssCatProtocol

ACMGR = TypeVar('ACMGR', bound='AssCatManager')
ACAPP = TypeVar('ACAPP', bound='AssCatApp')


class AssCatManager:

    def __init__(self, loop: AbstractEventLoop | None = None):
        self._loop: AbstractEventLoop = get_event_loop() if loop is None else loop
        self._listeners: List[Server] | None = []
        self._conns_in: Dict[int,] = {}
        self._conns_out: Dict[int,] = {}
        self._active_session_id: int | None = None
        self._protocol: str | None = None
        self._app: ACAPP | None = None
        self._logger = setup_logger(__name__)

    @property
    def listeners(self) -> List[Optional[Server]]:
        return self._listeners

    @property
    def listeners_count(self):
        return len(self._listeners)

    @property
    def incoming_connections_count(self):
        return len(self._conns_in)

    async def create_listener(
            self,
            host='127.0.0.1',
            port=8888,
            ssl: bool = None
    ) -> Tuple[int, Server]:

        if ssl and not isinstance(ssl, SSLContext):
            ssl = None

        l_id = self.listeners_count
        server: Server = await self._loop.create_server(
            protocol_factory=lambda: AssCatProtocol(self._loop, self, l_id),
            host=host,
            port=port,
            reuse_port=True,
            reuse_address=True,
            ssl=ssl,
            start_serving=False,
        )
        self._listeners.append(server)
        return l_id, server

    async def start_listener(self, _id):
        await self._listeners[_id].start_serving()
        self._logger.info(f'Started listener #{_id}')

    async def stop_listener(self, _id):
        if self._listeners:
            listener = self.get_listener(_id)
            self._listeners[_id].close()
            self._listeners.remove(listener)
            self._logger.info(f'Stopped listener #{_id}')

    def get_listener(self, _id):
        return self._listeners[_id]

    def client_connected_cb(self, session: AssCatProtocol, peername) -> None:
        sid = session.session_id
        self._conns_in.update({
            sid: session
        })
        self._logger.info(f'Connection from {peername}, {sid}')
        if not self._active_session_id:
            self._active_session_id = sid

    def client_disconnected_cb(self, session_id):
        del self._conns_in[session_id]
        if session_id == self._active_session_id:
            self._active_session_id = None

    def set_textual_app(self, app):
        self._app = app
        self._logger.info('Linked Textual app')

    def _shutdown(self):
        self._logger.info('Shutting down manager...')
        self._closing = True
        for listener in self._listeners:
            listener.close()

    async def shutdown(self):
        self._shutdown()


async def acm_create_listener():
    acm = AssCatManager()
    await acm.create_listener()
    listener = acm.get_listener(0)
    await acm.start_listener(0)
    async with listener:
        await listener.serve_forever()

if __name__ == '__main__':
    uvloop.run(acm_create_listener())
    exit(0)
