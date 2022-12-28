from android.util import Log
import io
import sys


# The maximum length of a log message in bytes, including the level marker and tag, is defined
# as LOGGER_ENTRY_MAX_PAYLOAD in platform/system/logging/liblog/include/log/log.h. As of API
# level 30, messages longer than this will be be truncated by logcat. This limit has already
# been reduced at least once in the history of Android (from 4076 to 4068 between API level 23
# and 26), so leave some headroom.
MAX_LINE_LEN_BYTES = 4000

# UTF-8 uses a maximum of 4 bytes per character. However, if the actual number of bytes
# per character is smaller than that, then TextIOWrapper may join multiple consecutive
# writes before passing them to the binary stream.
MAX_LINE_LEN_CHARS = MAX_LINE_LEN_BYTES // 4


def initialize():
    sys.stdin = EmptyInputStream()

    # Log levels are consistent with those used by Java.
    sys.stdout = TextLogStream(Log.INFO, "python.stdout")
    sys.stderr = TextLogStream(Log.WARN, "python.stderr")


class EmptyInputStream(io.TextIOBase):
    def readable(self):
        return True

    def read(self, size=None):
        return ""

    def readline(self, size=None):
        return ""


class TextLogStream(io.TextIOWrapper):
    def __init__(self, level, tag):
        super().__init__(BinaryLogStream(self, level, tag),
                         encoding="UTF-8", errors="backslashreplace",
                         line_buffering=True)
        self._CHUNK_SIZE = MAX_LINE_LEN_BYTES

    def __repr__(self):
        return f"<TextLogStream {self.buffer.tag!r}>"

    def write(self, s):
        if not isinstance(s, str):
            # Same wording as TextIOWrapper.write.
            raise TypeError(f"write() argument must be str, not {type(s).__name__}")

        # To avoid combining multiple lines into a single log message, we split the string
        # into separate lines before sending it to the superclass. Note that
        # "".splitlines() == [], so nothing will be logged in that case.
        for line, line_keepends in zip(s.splitlines(), s.splitlines(keepends=True)):
            # Simplify the later stages by translating all newlines into "\n".
            if line != line_keepends:
                line += "\n"
            while line:
                super().write(line[:MAX_LINE_LEN_CHARS])
                line = line[MAX_LINE_LEN_CHARS:]
        return len(s)


class BinaryLogStream(io.RawIOBase):
    def __init__(self, text_stream, level, tag):
        self.text_stream = text_stream
        self.level = level
        self.tag = tag

    def __repr__(self):
        return f"<BinaryLogStream {self.tag!r}>"

    def writable(self):
        return True

    def write(self, b):
        # This form of `str` throws a TypeError on any non-bytes-like object, as opposed
        # to the AttributeError we would probably get from trying to call `encode`.
        s = str(b, self.text_stream.encoding, self.text_stream.errors)

        # Writing an empty string to the stream should have no effect. Writing an empty
        # line should log an empty line, but Logcat would drop that on some devices, at
        # least according to the command-line `logcat` tool. So we log a single space
        # instead.
        if s:
            # TODO: replace with removesuffix once our minimum Python version is 3.9.
            if s.endswith("\n"):
                s = s[:-1]
            Log.println(self.level, self.tag, s or " ")
        return len(b)
