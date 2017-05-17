import unittest

from chaquopy import autoclass

from chaquopy.signatures import *

class SignaturesTest(unittest.TestCase):

    def test_return_types(self):

        # Void
        sig = signature(jvoid, [])
        self.assertEquals(sig, "()V")

        # Boolean
        sig = signature(jboolean, [])
        self.assertEquals(sig, "()Z")

        # Byte
        sig = signature(jbyte, [])
        self.assertEquals(sig, "()B")

        # Char
        sig = signature(jchar, [])
        self.assertEquals(sig, "()C")

        # Double
        sig = signature(jdouble, [])
        self.assertEquals(sig, "()D")

        # Float
        sig = signature(jfloat, [])
        self.assertEquals(sig, "()F")

        # Int 
        sig = signature(jint, [])
        self.assertEquals(sig, "()I")

        # Long 
        sig = signature(jlong, [])
        self.assertEquals(sig, "()J")

        # Short 
        sig = signature(jshort, [])
        self.assertEquals(sig, "()S")

        # Object return method
        String = autoclass("java.lang.String")
        sig = signature(String, [])
        self.assertEquals(sig, "()Ljava/lang/String;")

        # Array return
        sig = signature(JArray(jint), [])
        self.assertEquals(sig, "()[I")

    def test_params(self):
        String = autoclass("java.lang.String")

        # Return void, takes objects as parameters
        sig = signature(jvoid, [String, String])
        self.assertEquals(sig, "(Ljava/lang/String;Ljava/lang/String;)V")

        # Multiple array parameter types
        sig = signature(jvoid, [JArray(jint), JArray(jboolean)])
        self.assertEquals(sig, "([I[Z)V")

