from asyncio import (
    AbstractEventLoop,
    StreamWriter,
    StreamReader,
)
from typing import List


class Session:

    def __init__(
            self,
            session_id: int,
            loop: AbstractEventLoop,
            protocol,
    ):
        self.session_id = session_id
        self.loop = loop
        self.protocol = protocol
        self.manager = protocol.manager
        self.socket_transport = protocol.transport
        self.socket_reader: StreamReader = protocol.reader
        self.socket_writer: StreamWriter = protocol.writer
        self.stdin_reader: StreamReader = protocol.manager.stdin_reader
        self.stdin_transport = protocol.manager.stdin_transport
        self.stdout_writer: StreamWriter = protocol.manager.stdout_writer
        self._session_buffer: bytes = b''
        self._cmd_history: List[bytes] = []
        self.__index: int = 0

    async def __aiter__(self):
        self.__index = 0
        return self

    async def __anext__(self):
        if self.__index < len(self.manager.sessions):
            session = self.manager.sessions[self.__index]
            self.__index += 1
            return session
        else:
            raise StopAsyncIteration
