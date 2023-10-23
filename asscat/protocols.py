from asyncio import (
    AbstractEventLoop,
    Transport,
    StreamReader,
    StreamWriter, Protocol
)
from asyncio.trsock import TransportSocket
from typing import Optional, Union

from asscat.sessions import Session


class RevshellProtocol(Protocol):

    def __init__(self, loop: AbstractEventLoop, manager):
        self.loop = loop
        self.manager = manager
        self.transport: Optional[Union[Transport, TransportSocket]] = None
        self.reader = StreamReader(loop=loop)
        self.session: Optional[Session] = None
        self.stdout_writer: StreamWriter = manager.stdout_writer
        self.is_connected = False

    def connection_made(self, transport):
        self.is_connected = True
        self.transport = transport
        sessions_count = len(self.manager.sessions)
        session = Session(
            loop=self.loop,
            protocol=self,
            session_id=sessions_count,
        )
        self.manager.sessions.append(session)
        self.session = session
        print(f'Connection made from {transport.get_extra_info("peername")}')
        self.loop.create_task(self.session.send_cmd())

    def data_received(self, data: bytes):
        self.reader.feed_data(data)
        self.stdout_writer.transport.write(data)
        self.loop.create_task(self.session.send_cmd())

    def connection_lost(self, exc):
        self.is_connected = False
