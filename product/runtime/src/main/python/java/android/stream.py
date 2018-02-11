"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from android.util import Log
from io import TextIOBase
import sys


# LOGGER_ENTRY_MAX_PAYLOAD is defined as 4076 in
# android/platform/system/core/include/cutils/logger.h, but it looks like the level marker and
# tag are also included in this value.
MAX_LINE_LEN = 4060


def initialize():
    sys.stdin = EmptyInputStream()

    # Log levels are consistent with those used by Java.
    sys.stdout = LogOutputStream(Log.INFO, "python.stdout")
    sys.stderr = LogOutputStream(Log.WARN, "python.stderr")


class EmptyInputStream(TextIOBase):
    def readable(self):
        return True

    def read(self, size=None):
        return ""

    def readline(self, size=None):
        return ""


class LogOutputStream(TextIOBase):
    def __init__(self, level, tag):
        TextIOBase.__init__(self)
        self.level = level
        self.tag = tag

    def writable(self):
        return True

    # print() calls write() separately to write the ending newline, which will unfortunately
    # produce multiple log messages. The only alternatives would be buffering, or ignoring
    # empty lines, both of which would be bad for debugging.
    def write(self, s):
        if sys.version_info[0] < 3 and isinstance(s, str):
            s = s.decode("UTF-8", "replace")
        for line in s.splitlines():  # "".splitlines() == [], so nothing will be logged.
            line = line or " "  # Empty log messages are ignored.
            while True:
                Log.println(self.level, self.tag, line[:MAX_LINE_LEN])
                line = line[MAX_LINE_LEN:]
                if not line:
                    break
