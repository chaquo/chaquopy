# Adapted from Python 3.6 (the relevant functions are not present in Python 2.7).

from __future__ import absolute_import, division, print_function

import codecs
import re

from six.moves.builtins import open as _builtin_open

__all__ = ["read"]


cookie_re = re.compile(r'^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)')
blank_re = re.compile(br'^[ \t\f]*(?:[#\r\n]|$)')


def _get_normal_name(orig_enc):
    """Imitates get_normal_name in tokenizer.c."""
    # Only care about the first 12 characters.
    enc = orig_enc[:12].lower().replace("_", "-")
    if enc == "utf-8" or enc.startswith("utf-8-"):
        return "utf-8"
    if enc in ("latin-1", "iso-8859-1", "iso-latin-1") or \
       enc.startswith(("latin-1-", "iso-8859-1-", "iso-latin-1-")):
        return "iso-8859-1"
    return orig_enc


def detect_encoding(readline):
    """
    The detect_encoding() function is used to detect the encoding that should
    be used to decode a Python source file.  It requires one argument, readline,
    in the same way as the tokenize() generator.

    It will call readline a maximum of twice, and return the encoding used
    (as a string) and a list of any lines (left as bytes) it has read in.

    It detects the encoding from the presence of a utf-8 bom or an encoding
    cookie as specified in pep-0263.  If both a bom and a cookie are present,
    but disagree, a SyntaxError will be raised.  If the encoding cookie is an
    invalid charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
    'utf-8-sig' is returned.

    If no encoding is specified, then the default of 'utf-8' will be returned.
    """
    try:
        filename = readline.__self__.name
    except AttributeError:
        filename = None
    bom_found = False
    encoding = None
    default = 'utf-8'
    def read_or_stop():
        try:
            return readline()
        except StopIteration:
            return b''

    first = read_or_stop()
    if first.startswith(codecs.BOM_UTF8):
        bom_found = True
        first = first[3:]
        default = 'utf-8-sig'
    if not first:
        return default, []

    encoding = find_cookie(filename, first, bom_found)
    if encoding:
        return encoding, [first]
    if not blank_re.match(first):
        return default, [first]

    second = read_or_stop()
    if not second:
        return default, [first]

    encoding = find_cookie(filename, second, bom_found)
    if encoding:
        return encoding, [first, second]

    return default, [first, second]


def find_cookie(filename, line, bom_found=False):
    try:
        # Decode as UTF-8. Either the line is an encoding declaration,
        # in which case it should be pure ASCII, or it must be UTF-8
        # per default encoding.
        line_string = line.decode('utf-8')
    except UnicodeDecodeError:
        msg = "invalid or missing encoding declaration"
        if filename is not None:
            msg = '{} for {!r}'.format(msg, filename)
        raise SyntaxError(msg)

    match = cookie_re.match(line_string)
    if not match:
        return None
    encoding = _get_normal_name(match.group(1))
    try:
        codecs.lookup(encoding)
    except LookupError:
        # This behaviour mimics the Python interpreter
        if filename is None:
            msg = "unknown encoding: " + encoding
        else:
            msg = "unknown encoding for {!r}: {}".format(filename, encoding)
        raise SyntaxError(msg)

    if bom_found:
        if encoding != 'utf-8':
            # This behaviour mimics the Python interpreter
            if filename is None:
                msg = 'encoding problem: utf-8'
            else:
                msg = 'encoding problem for {!r}: utf-8'.format(filename)
            raise SyntaxError(msg)
        encoding += '-sig'
    return encoding


def read(filename):
    """Return the file content as a Unicode string, using the encoding detected by
    detect_encoding().
    """
    lines = []
    with _builtin_open(filename, 'rb') as buffer:
        encoding, d_e_lines = detect_encoding(buffer.readline)
        buffer.seek(0)
        for line_no, line in enumerate(codecs.getreader(encoding)(buffer)):
            if (line_no < len(d_e_lines)) and find_cookie(filename, d_e_lines[line_no]):
                continue  # Skip over the encoding declaration: it confuses Python 2's compile().
            lines.append(line)
    return "".join(lines)
