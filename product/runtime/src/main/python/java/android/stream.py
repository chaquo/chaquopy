"""Copyright (c) 2020 Chaquo Ltd. All rights reserved."""

from android.util import Log
import io
import sys


# The maximum length of a log message in bytes, including the level marker and tag, is defined
# as LOGGER_ENTRY_MAX_PAYLOAD in platform/system/logging/liblog/include/log/log.h. As of API
# level 30, messages longer than this will be be truncated by logcat. This limit has already
# been reduced at least once in the history of Android (from 4076 to 4068 between API level 23
# and 26), so leave some headroom.
MAX_LINE_LEN = 4000


def initialize():
    sys.stdin = EmptyInputStream()

    # Log levels are consistent with those used by Java.
    sys.stdout = LogOutputStream(Log.INFO, "python.stdout")
    sys.stderr = LogOutputStream(Log.WARN, "python.stderr")


class EmptyInputStream(io.TextIOBase):
    def readable(self):
        return True

    def read(self, size=None):
        return ""

    def readline(self, size=None):
        return ""


class LogOutputStream(io.TextIOBase):
    def __init__(self, level, tag):
        self.level = level
        self.tag = tag
        self.buffer = BytesOutputWrapper(self)

    def __repr__(self):
        return f"<LogOutputStream {self.tag!r}>"

    @property
    def encoding(self):
        return "UTF-8"

    @property
    def errors(self):
        return "backslashreplace"

    def writable(self):
        return True

    # print() calls write() separately to write the ending newline, which will unfortunately
    # produce multiple log messages. The only alternatives would be buffering, or ignoring
    # empty lines, both of which would be bad for debugging.
    def write(self, s):
        if not isinstance(s, str):
            # Same wording as the standard TextIOWrapper stdout.
            raise TypeError(f"write() argument must be str, not {type(s).__name__}")

        for line in s.splitlines():  # "".splitlines() == [], so nothing will be logged.
            line = line or " "  # Empty lines are dropped by logcat, so pass a single space.
            while line:
                # TODO #5730: max line length should be measured in bytes.
                Log.println(self.level, self.tag, line[:MAX_LINE_LEN])
                line = line[MAX_LINE_LEN:]
        return len(s)


class BytesOutputWrapper(io.RawIOBase):
    def __init__(self, stream):
        self.stream = stream

    def __repr__(self):
        return f"<BytesOutputWrapper {self.stream}>"

    @property
    def encoding(self):
        return self.stream.encoding

    @property
    def errors(self):
        return self.stream.errors

    def writable(self):
        return self.stream.writable()

    def write(self, b):
        # This form of `str` throws a TypeError on any non-bytes-like object.
        self.stream.write(str(b, self.stream.encoding, self.stream.errors))
        return len(b)
