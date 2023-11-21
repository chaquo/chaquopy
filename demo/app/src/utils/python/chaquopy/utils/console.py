from io import TextIOBase
from queue import Queue


class ConsoleInputStream(TextIOBase):
    """Receives input in on_input in one thread (non-blocking), and provides a read interface
    in another thread (blocking).
    """
    def __init__(self, task):
        self.task = task
        self.queue = Queue()
        self.buffer = ""
        self.eof = False

    @property
    def encoding(self):
        return "UTF-8"

    @property
    def errors(self):
        return "strict"  # UTF-8 encoding should never fail.

    def readable(self):
        return True

    def on_input(self, input):
        if self.eof:
            raise ValueError("Can't add more input after EOF")
        if input is None:
            self.eof = True
        self.queue.put(input)

    def read(self, size=None):
        if size is not None and size < 0:
            size = None
        buffer = self.buffer
        while (self.queue is not None) and ((size is None) or (len(buffer) < size)):
            if self.queue.empty():
                self.task.onInputState(True)
            input = self.queue.get()
            self.task.onInputState(False)
            if input is None:  # EOF
                self.queue = None
            else:
                buffer += input

        result = buffer if (size is None) else buffer[:size]
        self.buffer = buffer[len(result):]
        return result

    def readline(self, size=None):
        if size is not None and size < 0:
            size = None
        chars = []
        while (size is None) or (len(chars) < size):
            c = self.read(1)
            if not c:
                break
            chars.append(c)
            if c == "\n":
                break

        return "".join(chars)


class ConsoleOutputStream(TextIOBase):
    """Passes each write to the underlying stream, and also to the given method, which must take
    a single string argument.
    """
    def __init__(self, stream, obj, method_name):
        self.stream = stream
        self.method = getattr(obj, method_name)

    def __repr__(self):
        return f"<ConsoleOutputStream {self.stream}>"

    def __getattribute__(self, name):
        # Forward all attributes that have useful implementations.
        if name in [
            "close", "closed", "flush", "writable",  # IOBase
            "encoding", "errors", "newlines", "buffer", "detach",  # TextIOBase
            "line_buffering", "write_through", "reconfigure",  # TextIOWrapper
        ]:
            return getattr(self.stream, name)
        else:
            return super().__getattribute__(name)

    def write(self, s):
        # Pass the write to the underlying stream first, so that if it throws an exception, the
        # app crashes in the same way whether it's using ConsoleOutputStream or not (#5712).
        result = self.stream.write(s)
        self.method(s)
        return result
