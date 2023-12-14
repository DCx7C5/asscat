from socket import socket, AF_INET, AF_INET6, SOCK_STREAM, SOCK_DGRAM
from threading import Thread
from typing import Literal, Callable

from asscat.transports import SocketTransport
from asscat.exceptions import ServerAddressFamilyError, ServerSocketTypeException


class Server(Thread, SocketTransport):

    def __init__(
            self,
            transport: SocketTransport,
            connection_made_cb: Callable,
    ):
        super().__init__(daemon=True)
        self._addr = (ip, port)
        self._ssl = ssl

        s_type = s_type.upper()

        self._sock = None

        if s_type == 'TCP':
            self._s_type = SOCK_STREAM
        elif s_type == 'UDP':
            self._s_type = SOCK_DGRAM
        else:
            raise ServerSocketTypeException()

        if '4' in str(addr_fam):
            self._addr_fam = AF_INET
        elif '6' in str(addr_fam):
            self._addr_fam = AF_INET6
        else:
            raise ServerAddressFamilyError()

    def run(self):
        self._sock = socket(family=self._addr_fam, type=self._s_type)
