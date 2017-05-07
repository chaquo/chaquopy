from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import unittest
from chaquopy import autoclass, JavaException


class AssignableFrom(unittest.TestCase):

    def test_assignable(self):
        ArrayList = autoclass('java.util.ArrayList')
        Object = autoclass('java.lang.Object')

        a = ArrayList()
        # addAll accept Collection, Object must failed
        self.assertRaises(TypeError, a.addAll, Object())
        # while adding another ArrayList must be ok.
        a.addAll(ArrayList())
