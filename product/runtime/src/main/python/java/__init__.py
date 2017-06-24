"""Copyright (c) 2017 Chaquo Ltd. All rights reserved."""
from __future__ import absolute_import, division, print_function

# Chaquopy contains parts of the following open-source software:
#
# PyJNIus (https://github.com/kivy/pyjnius/)
# Copyright (c) 2010-2017 Kivy Team and other contributors
#
# pip (https://github.com/pypa/pip/)
# Copyright (c) 2008-2016 The pip developers


# On Android, the native module is stored separately to the Python modules.
from pkgutil import extend_path
__path__ = extend_path(__path__, __name__)

from .chaquopy import *  # noqa
jclass = jklass
from .signatures import *  # noqa

# This is the public API.
__all__ = ["cast", "JavaException", "jclass",
           "jboolean", "jbyte", "jshort", "jint", "jlong", "jfloat", "jdouble", "jchar",
           "jarray"]
