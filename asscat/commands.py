from asyncio import AbstractEventLoop
from typing import Optional, List


class Cmds:
    __slots__ = ('_loop', '_commands')

    def __init__(self, loop):
        self._loop: AbstractEventLoop = loop
        self._commands = {
            'sessions': self.sessions,
            'back': self.back,
            'exit': self.exit,
        }

    async def parse(self, raw_cmd: bytes):
        cmd = raw_cmd.decode().split()
        if cmd[0] in self._commands.keys():
            return await self._commands[cmd[0]](cmd[1:])
        return raw_cmd

    async def register(self, func, name):
        self._commands.update({name: func})

    async def sessions(self, args: List[str]):
        if not args:
            pass

    async def help(self):
        pass

    async def exit(self):
        pass



async def command(func):
    async def wrapper_func():
        # Do something before the function.
        func()
        # Do something after the function.
    return wrapper_func



async def back(*args, **kwargs):
    pass