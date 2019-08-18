# This package is used by chaquopy.test.test_android.


# Test relative imports from a first-level package (package1/package11/__init__.py
# performs the same imports from a second-level package context).
def test_relative(self):
    from . import java, python
    self.assertEqual("java 1", java.x)
    self.assertEqual("python 1", python.x)

    from .package11 import java, python
    self.assertEqual("java 11", java.x)
    self.assertEqual("python 11", python.x)

    from .package11.package111 import java, python
    self.assertEqual("java 111", java.x)
    self.assertEqual("python 111", python.x)

    from .package12 import java, python
    self.assertEqual("java 12", java.x)
    self.assertEqual("python 12", python.x)

    from .package12.package121 import java, python
    self.assertEqual("java 121", java.x)
    self.assertEqual("python 121", python.x)

    # Relative imports can't pass through the top level (http://bugs.python.org/issue30840).
    # Error wording varies across Python versions.
    with self.assertRaisesRegexp(ValueError,
                                 r"^[Aa]ttempted relative import beyond top(-?)level package$"):
        from .. import whatever  # noqa: F401


def test_relative_implicit(self):
    import python
    self.assertEqual("python 1", python.x)
