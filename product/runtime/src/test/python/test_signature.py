from __future__ import absolute_import, division, print_function

import unittest

from chaquopy import autoclass

from chaquopy.signatures import *

class SignaturesTest(unittest.TestCase):

    def test_return_types(self):

        # Void
        sig = jni_method_sig(jvoid, [])
        self.assertEquals(sig, "()V")

        # Boolean
        sig = jni_method_sig(jboolean, [])
        self.assertEquals(sig, "()Z")

        # Byte
        sig = jni_method_sig(jbyte, [])
        self.assertEquals(sig, "()B")

        # Char
        sig = jni_method_sig(jchar, [])
        self.assertEquals(sig, "()C")

        # Double
        sig = jni_method_sig(jdouble, [])
        self.assertEquals(sig, "()D")

        # Float
        sig = jni_method_sig(jfloat, [])
        self.assertEquals(sig, "()F")

        # Int 
        sig = jni_method_sig(jint, [])
        self.assertEquals(sig, "()I")

        # Long 
        sig = jni_method_sig(jlong, [])
        self.assertEquals(sig, "()J")

        # Short 
        sig = jni_method_sig(jshort, [])
        self.assertEquals(sig, "()S")

        # Object return method
        String = autoclass("java.lang.String")
        sig = jni_method_sig(String, [])
        self.assertEquals(sig, "()Ljava/lang/String;")

        # Array return
        sig = jni_method_sig(jarray(jint), [])
        self.assertEquals(sig, "()[I")

    def test_params(self):
        String = autoclass("java.lang.String")

        # Return void, takes objects as parameters
        sig = jni_method_sig(jvoid, [String, String])
        self.assertEquals(sig, "(Ljava/lang/String;Ljava/lang/String;)V")

        # Multiple array parameter types
        sig = jni_method_sig(jvoid, [jarray(jint), jarray(jboolean)])
        self.assertEquals(sig, "([I[Z)V")

