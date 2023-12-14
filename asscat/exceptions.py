import traceback


class BaseExceptionWithTraceback(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.traceback = traceback.format_exc()

    def __str__(self):
        return f"{super().__str__()}\nTraceback:\n{self.traceback}"


class SocketException(BaseExceptionWithTraceback): ...


class ServerException(BaseExceptionWithTraceback): ...


class ServerSocketTypeException(ServerException): ...


class ServerAddressFamilyError(ServerException): ...


class BufferLimitError(ServerException): ...