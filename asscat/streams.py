import sys
from abc import ABC
from asyncio import (
    AbstractEventLoop,
    StreamReader,
    StreamWriter,
    StreamReaderProtocol, sleep, Future, IncompleteReadError, LimitOverrunError,
)
from asyncio.streams import FlowControlMixin  # noqa
from typing import Optional

from asscat.exceptions import BufferLimitError

BUF_LIMIT = 4096


class AssCatReader:

    __slots__ = ('_loop', '_limit', '_buffer', '_eof', '_waiter',
                 '_exception', '_transport', '_paused', '_traceback')

    def __init__(self, loop: AbstractEventLoop, limit: int = BUF_LIMIT):
        self._loop: AbstractEventLoop = loop

        if not isinstance(limit, int):
            raise BufferLimitError("Buffer must be an integer")

        if limit <= 0:
            raise BufferLimitError("Buffer limit must be greater zero")

        self._limit = limit
        self._buffer: bytearray = bytearray()
        self._eof: bool = False
        self._waiter: Optional[Future] = None
        self._exception: Optional[Exception] = None
        self._transport = None
        self._paused: bool = False

    def __repr__(self):
        info = ['StreamReader']
        if self._buffer:
            info.append(f'{len(self._buffer)} bytes')
        if self._eof:
            info.append('eof')
        if self._limit != BUF_LIMIT:
            info.append(f'limit={self._limit}')
        if self._waiter:
            info.append(f'waiter={self._waiter!r}')
        if self._exception:
            info.append(f'exception={self._exception!r}')
        if self._transport:
            info.append(f'transport={self._transport!r}')
        if self._paused:
            info.append('paused')
        return '<{}>'.format(' '.join(info))

    def exception(self):
        return self._exception

    def set_exception(self, exc):
        self._exception = exc
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_exception(exc)

    def _wakeup_waiter(self):
        """Wakeup read*() functions waiting for data or EOF."""
        waiter = self._waiter
        if waiter is not None:
            self._waiter = None
            if not waiter.cancelled():
                waiter.set_result(None)

    def _maybe_resume_transport(self):
        if self._paused and len(self._buffer) <= self._limit:
            self._paused = False
            self._transport.resume_reading()

    def feed_eof(self):
        self._eof = True
        self._wakeup_waiter()

    def at_eof(self):
        """Return True if the buffer is empty and 'feed_eof' was called."""
        return self._eof and not self._buffer

    async def _wait_for_data(self, func_name):
        """Wait until feed_data() or feed_eof() is called.

        If stream was paused, automatically resume it.
        """
        # StreamReader uses a future to link the protocol feed_data() method
        # to a read coroutine. Running two read coroutines at the same time
        # would have an unexpected behaviour. It would not possible to know
        # which coroutine would get the next data.
        if self._waiter is not None:
            raise RuntimeError(
                f'{func_name}() called while another coroutine is '
                f'already waiting for incoming data')

        assert not self._eof, '_wait_for_data after EOF'

        # Waiting for data while paused will make deadlock, so prevent it.
        # This is essential for readexactly(n) for case when n > self._limit.
        if self._paused:
            self._paused = False
            self._transport.resume_reading()

        self._waiter = self._loop.create_future()
        try:
            await self._waiter
        finally:
            self._waiter = None

    async def readline(self):
        """Read chunk of data from the stream until newline (b'\n') is found.

        On success, return chunk that ends with newline. If only partial
        line can be read due to EOF, return incomplete line without
        terminating newline. When EOF was reached while no bytes read, empty
        bytes object is returned.

        If limit is reached, ValueError will be raised. In that case, if
        newline was found, complete line including newline will be removed
        from internal buffer. Else, internal buffer will be cleared. Limit is
        compared against part of the line without newline.

        If stream was paused, this function will automatically resume it if
        needed.
        """
        sep = b'\n'
        seplen = len(sep)
        try:
            line = await self.read_until(sep)
        except IncompleteReadError as e:
            return e.partial
        except LimitOverrunError as e:
            if self._buffer.startswith(sep, e.consumed):
                del self._buffer[:e.consumed + seplen]
            else:
                self._buffer.clear()
            self._maybe_resume_transport()
            raise ValueError(e.args[0])
        return line

    async def read_until(self, separator=b'\n'):
        """Read data from the stream until ``separator`` is found.

        On success, the data and separator will be removed from the
        internal buffer (consumed). Returned data will include the
        separator at the end.

        Configured stream limit is used to check result. Limit sets the
        maximal length of data that can be returned, not counting the
        separator.

        If an EOF occurs and the complete separator is still not found,
        an IncompleteReadError exception will be raised, and the internal
        buffer will be reset.  The IncompleteReadError.partial attribute
        may contain the separator partially.

        If the data cannot be read because of over limit, a
        LimitOverrunError exception  will be raised, and the data
        will be left in the internal buffer, so it can be read again.
        """
        sep_len = len(separator)
        if sep_len == 0:
            raise ValueError('Separator should be at least one-byte string')

        if self._exception is not None:
            raise self._exception

        # `offset` is the number of bytes from the beginning of the buffer
        # where there is no occurrence of `separator`.
        offset = 0

        # Loop until we find `separator` in the buffer, exceed the buffer size,
        # or an EOF has happened.
        while True:
            buflen = len(self._buffer)

            # Check if we now have enough data in the buffer for `separator` to
            # fit.
            if buflen - offset >= sep_len:
                isep = self._buffer.find(separator, offset)

                if isep != -1:
                    # `separator` is in the buffer. `isep` will be used later
                    # to retrieve the data.
                    break

                # see upper comment for explanation.
                offset = buflen + 1 - sep_len
                if offset > self._limit:
                    raise LimitOverrunError(
                        'Separator is not found, and chunk exceed the limit',
                        offset)

            # Complete message (with full separator) may be present in buffer
            # even when EOF flag is set. This may happen when the last chunk
            # adds data which makes separator be found. That's why we check for
            # EOF *ater* inspecting the buffer.
            if self._eof:
                chunk = bytes(self._buffer)
                self._buffer.clear()
                raise IncompleteReadError(chunk, None)

            # _wait_for_data() will resume reading if stream was paused.
            await self._wait_for_data('readuntil')

        if isep > self._limit:
            raise LimitOverrunError(
                'Separator is found, but chunk is longer than limit', isep)

        chunk = self._buffer[:isep + sep_len]
        del self._buffer[:isep + sep_len]
        self._maybe_resume_transport()
        return bytes(chunk)

    async def read(self, n=-1):
        """Read up to `n` bytes from the stream.

        If `n` is not provided or set to -1,
        read until EOF, then return all read bytes.
        If EOF was received and the internal buffer is empty,
        return an empty bytes object.

        If `n` is 0, return an empty bytes object immediately.

        If `n` is positive, return at most `n` available bytes
        as soon as at least 1 byte is available in the internal buffer.
        If EOF is received before any byte is read, return an empty
        bytes object.

        Returned value is not limited with limit, configured at stream
        creation.

        If stream was paused, this function will automatically resume it if
        needed.
        """

        if self._exception is not None:
            raise self._exception

        if n == 0:
            return b''

        if n < 0:
            # This used to just loop creating a new waiter hoping to
            # collect everything in self._buffer, but that would
            # deadlock if the subprocess sends more than self.limit
            # bytes.  So just call self.read(self._limit) until EOF.
            blocks = []
            while True:
                block = await self.read(self._limit)
                if not block:
                    break
                blocks.append(block)
            return b''.join(blocks)

        if not self._buffer and not self._eof:
            await self._wait_for_data('read')

        # This will work right even if buffer is less than n bytes
        data = bytes(self._buffer[:n])
        del self._buffer[:n]

        self._maybe_resume_transport()
        return data

    def __aiter__(self):
        return self

    async def __anext__(self):
        val = await self.readline()
        if val == b'':
            raise StopAsyncIteration
        return val


class AssCatWriter:
    """Transport wrapper"""
    __slots__ = ('_transport', '_protocol', '_reader', '_loop',
                 '_complete_fut',)

    def __init__(
            self,
            transport,
            protocol,
            reader: StreamReader,
            loop: AbstractEventLoop,
    ):
        self._loop: AbstractEventLoop = loop
        self._transport = transport

        self._protocol = protocol
        self._reader: StreamReader = reader
        self._complete_fut = self._loop.create_future()
        self._complete_fut.set_result(None)

    @property
    def transport(self):
        return self._transport

    @property
    def protocol(self):
        return self._protocol

    @property
    def reader(self):
        return self._reader

    def write(self, data):
        self._transport.write(data)

    def writelines(self, data):
        self._transport.writelines(data)

    def write_eof(self):
        return self._transport.write_eof_to_stdout()

    def can_write_eof(self):
        return self._transport.can_write_eof()

    def close(self):
        return self._transport.close()

    def is_closing(self):
        return self._transport.is_closing()

    async def wait_closed(self):
        await self._protocol._get_close_waiter(self)

    def get_extra_info(self, name, default=None):
        return self._transport.get_extra_info(name, default)

    async def _check_for_exception(self):
        """Checks for exception and sends it to exc handler"""
        exc = self._reader.exception()
        if isinstance(exc, Exception):
            raise exc

    async def flush(self) -> None:
        """Flush the stdout write buffer"""
        if isinstance(self._reader, StreamReader):
            await self._check_for_exception()
        if self._transport.is_closing():
            await sleep(.1)
        await self._protocol._drain_helper()  # noqa: pm

    async def start_tls(self, sslcontext, *,
                        server_hostname=None,
                        ssl_handshake_timeout=None):
        """Upgrade an existing stream-based connection to TLS."""
        server_side = self._protocol._client_connected_cb is not None  # noqa: pm
        protocol = self._protocol
        await self.flush()
        new_transport = await self._loop.start_tls(
            transport=self._transport, protocol=protocol, sslcontext=sslcontext,
            server_side=server_side, server_hostname=server_hostname,
            ssl_handshake_timeout=ssl_handshake_timeout)
        self._transport = new_transport
        protocol._replace_writer(self)  # noqa: pm

    def __del__(self):
        if not self._transport.is_closing():
            self.close()


class StdInReader(AssCatReader):
    _source_traceback = None
    __slots__ = ('_loop', )

    def __init__(self, loop: AbstractEventLoop):
        self._loop: AbstractEventLoop = loop


class Stream(ABC):
    """
    Abstract class that wraps a reader, writer
    or both to represent a connection
    """

    def __init__(self):
        self._loop: Optional[AbstractEventLoop] = None
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None

    async def read(self) -> bytes:
        return await self._reader.read(BUF_LIMIT)

    async def readchar(self) -> bytes:
        return await self._reader.read(1)

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def write(self, data: bytes):
        self._writer.write(data)
        await self._writer.drain()

    async def close(self):
        self._writer.close()


class StdIOStream(Stream):
    __slots__ = ('_loop', '_reader', '_writer')

    def __init__(self, loop: AbstractEventLoop):
        super().__init__()
        self._loop = loop

    async def _create_reader(self):
        self._reader = StreamReader()
        transport, _ = await self._loop.connect_read_pipe(
            protocol_factory=lambda: StreamReaderProtocol(self._reader, loop=self._loop),
            pipe=sys.stdin
        )

    async def _create_writer(self):
        transport, protocol = await self._loop.connect_write_pipe(
            protocol_factory=FlowControlMixin,
            pipe=sys.stdout
        )
        self._writer = StreamWriter(
            transport=transport,
            protocol=protocol,
            reader=self._reader,
            loop=self._loop
        )

    @classmethod
    async def create(cls, loop: AbstractEventLoop):
        self = cls(loop)
        await self._create_reader()
        await self._create_writer()
        return self


class SocketStream(Stream):
    __slots__ = ('_loop', '_reader', '_writer', '_out_history')

    def __init__(self, loop: AbstractEventLoop):
        super().__init__()
        self._loop = loop

    @classmethod
    def create(cls, loop: AbstractEventLoop, reader: AssCatReader, writer: AssCatWriter):
        self = cls(loop)
        self._reader = reader
        self._writer = writer
        return self
