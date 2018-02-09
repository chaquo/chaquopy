from __future__ import absolute_import, division, print_function

from io import TextIOBase
import sys

if sys.version_info[0] < 3:
    from Queue import Queue
else:
    from queue import Queue


class ConsoleOutputStream(TextIOBase):
    """Passes each write to the underlying stream, and also to the given method (which must take a
    single String argument) on the given Java object.
    """
    def __init__(self, activity, method_name, stream):
        TextIOBase.__init__(self)
        self.stream = stream
        self.activity = activity
        self.method_name = method_name

    def writable(self):
        return True

    def write(self, s):
        if sys.version_info[0] < 3 and isinstance(s, str):
            s = s.decode("UTF-8", "replace")
        self.stream.write(s)
        getattr(self.activity, self.method_name)(s)

    def flush(self):
        self.stream.flush()


class ConsoleInputStream(TextIOBase):
    """Receives input in on_input in one thread (non-blocking), and provides a read interface in 
    another thread (blocking). Input must be in unicode, but reads will return bytes in Python 2 or 
    unicode in Python 3.
    """
    def __init__(self, activity):
        TextIOBase.__init__(self)
        self.activity = activity
        self.queue = Queue()
        self.buffer = ""

    def readable(self):
        return True

    def on_input(self, input):
        self.queue.put(input)

    def read(self, size=None):
        if size < 0:
            size = None
        buffer = self.buffer
        while (size is None) or (len(buffer) < size):
            if self.queue.empty():
                self.activity.setInputState(True)
            buffer += self.queue.get()
            self.activity.setInputState(False)

        result = buffer if (size is None) else buffer[:size]
        self.buffer = buffer[len(result):]
        return result.encode("utf-8") if (sys.version_info[0] < 3) else result

    def readline(self, size=None):
        if size < 0:
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

    # FIXME add sentinel (None?) to queue on close, and return EOF?