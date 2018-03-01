"""Copyright (c) 2018 Chaquo Ltd. All rights reserved."""

from __future__ import absolute_import, division, print_function

from android.util import Log
from io import TextIOBase
import sys


# LOGGER_ENTRY_MAX_PAYLOAD is defined in system/core/include/cutils/logger.h or
# system/core/liblog/include/log/log_read.h, depending on Android version. The size of the
# level marker and tag are subtracted from this value. It has already been reduced at least
# once in the history of Android (from 4076 to 4068 between API level 23 and 26), so leave some
# headroom.
MAX_LINE_LEN = 4000


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

    @property
    def encoding(self):
        return "UTF-8"

    @property
    def errors(self):
        return "replace"

    def writable(self):
        return True

    # print() calls write() separately to write the ending newline, which will unfortunately
    # produce multiple log messages. The only alternatives would be buffering, or ignoring
    # empty lines, both of which would be bad for debugging.
    def write(self, s):
        if sys.version_info[0] < 3 and isinstance(s, str):
            u = s.decode(self.encoding, self.errors)
        else:
            u = s

        for line in u.splitlines():  # "".splitlines() == [], so nothing will be logged.
            line = line or " "  # Empty log messages are ignored.
            while line:
                Log.println(self.level, self.tag, line[:MAX_LINE_LEN])
                line = line[MAX_LINE_LEN:]

        return len(s)
