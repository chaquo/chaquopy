from io import TextIOBase
from queue import Queue


class ConsoleInputStream(TextIOBase):
    """Receives input in on_input in one thread (non-blocking), and provides a read interface
    in another thread (blocking).
    """
    def __init__(self, task):
        TextIOBase.__init__(self)
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
    """Passes each write to the underlying stream, and also to the given function, which must take
    a single string argument.
    """
    def __init__(self, stream, func):
        TextIOBase.__init__(self)
        self.stream = stream
        self.func = func

    @property
    def encoding(self):
        return self.stream.encoding

    @property
    def errors(self):
        return self.stream.errors

    def writable(self):
        return True

    def write(self, s):
        self.func(s)
        return self.stream.write(s)

    def flush(self):
        self.stream.flush()
