import io
import os
import sys
from socket import socket

from asscat.ac_types import AddressFamType, SocketType, SocketAddrType


class BaseTransport:
    __slots__ = ('_can_read', '_can_write', '_transport')

    def __init__(self, transport=None):
        self._can_write = False
        self._can_read = False
        self._transport = transport


class ReadTransport(BaseTransport):
    __slots__ = ()

    def __init__(self):
        super().__init__()
        self._can_read = True

    def read(self, n_bytes: int) -> bytes:
        pass

    def read_until(self, pattern, timeout) -> bytes:
        pass

    def read_line(self, timeout: float = None) -> bytes:
        b = b''

        return b


class WriteTransport(BaseTransport):
    __slots__ = ()

    def __init__(self):
        super().__init__()
        self._can_write = True


class LinuxFileTransport(ReadTransport, WriteTransport):
    __slots__ = ('_fd_no',)

    def __init__(self, path: str):
        super().__init__()
        fd_no = os.open(path, os.O_RDWR | os.O_CREAT)
        self._fd_no = fd_no


class StdIOTransport(ReadTransport, WriteTransport):
    __slots__ = ()

    def __init__(self, fd_in=0, fd_out=1, fd_err=2):
        super().__init__()



class SocketTransport(ReadTransport, WriteTransport):

    __slots__ = ('_sock',)

    def __init__(
            self,
            sock: socket = None,
            address: SocketAddrType = None,
            addr_fam: AddressFamType = None,
            sock_type: SocketType = None,
    ):
        super().__init__()
        if sock is None and address is None:
            raise ValueError('You must submit either submit a socket object as sock param'
                             'or an address tuple to instantiate this class')




