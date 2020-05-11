"""Copyright (c) 2020 Chaquo Ltd. All rights reserved.

Chaquopy contains parts of PyJNIus. The following notice applies to those parts:

    Copyright (c) 2010-2017 Kivy Team and other contributors

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in
    all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
    THE SOFTWARE.
"""

# On Android, the native module is stored separately to the Python modules.
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from .chaquopy import *  # noqa
from .chaquopy import chaquopy_init
from .primitive import *  # noqa

# This is the public API.
__all__ = [
    # .chaquopy
    "detach", "cast", "jclass",
    "dynamic_proxy", "static_proxy", "constructor", "method", "Override",
    "jarray", "set_import_enabled",

    # .primitive
    "jvoid", "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble", "jchar",
]


chaquopy_init()
