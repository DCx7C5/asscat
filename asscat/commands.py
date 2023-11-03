from asyncio import AbstractEventLoop
from typing import Optional, List


class Command:
    __slots__ = ('_loop', '_commands')

    def __init__(self):
        self._loop: Optional[AbstractEventLoop] = None
        self._commands: List[str] = []

    @classmethod
    async def parse(cls, manager, raw_cmd: bytes):
        cmd = raw_cmd.decode().split()
        if cmd[0] == 'session':
            manager.active_session = manager.sessions[int(cmd[1])]
            return None
        return raw_cmd
