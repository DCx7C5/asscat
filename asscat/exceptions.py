import traceback


class BufferSizeLimitError(Exception):
    def __init__(self, buffer_size):
        self.buffer_size = buffer_size
        self.traceback = traceback.format_exc()

    def __str__(self):
        return (f"Reader buffer size is zero or negative: "
                f"{self.buffer_size}\n\n{self.traceback}")
