from __future__ import absolute_import, division, print_function


Object_names = {"clone", "equals", "finalize", "getClass", "hashCode", "notify",
                "notifyAll", "toString", "wait"}

def assertDir(self, obj, expected):
    self.assertEqual(sorted(expected),
                     [s for s in dir(obj) if
                      not (s.startswith("__") or s.startswith("_chaquopy") or s == "<init>")])
