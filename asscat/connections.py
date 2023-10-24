from abc import ABC, abstractmethod


class BaseConnection(ABC):
    """
    Abstract class that wraps a reader, writer
    or both to represent a connection
    """

    def __init__(self):
        self.can_read = None
        self.can_write = None

    @abstractmethod
    async def recv(self):
        """Function to read from a stream"""
        raise NotImplementedError

    @abstractmethod
    async def write(self):
        """Function to write to a stream"""
        raise NotImplementedError

    @abstractmethod
    async def close_async(self):
        """Closes the connection asynchronously"""
        raise NotImplementedError

