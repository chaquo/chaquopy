from __future__ import absolute_import, division, print_function

from .test_android import *             # noqa: F401, F403
from .test_array import *               # noqa: F401, F403
from .test_conversion import *          # noqa: F401, F403
from .test_exception import *           # noqa: F401, F403
from .test_import import *              # noqa: F401, F403
from .test_java_api import *            # noqa: F401, F403
from .test_overload import *            # noqa: F401, F403
from .test_proxy import *               # noqa: F401, F403
from .test_reflect import *             # noqa: F401, F403
from .test_signatures import *          # noqa: F401, F403
from .test_static_proxy import *        # noqa: F401, F403
from .test_thread import *              # noqa: F401, F403


# Enable the following to profile the unit test run. This will not cover the `java` module
# initialization: that would require the above imports to be included as well.
# def load_tests(loader, tests, pattern):
#     from cProfile import Profile
#     from unittest import TestSuite

#     class ProfileTestSuite(TestSuite):
#         def run(self, result):
#             p = Profile()
#             p.enable()
#             TestSuite.run(self, result)
#             p.disable()
#             p.dump_stats("testPython.profile")

#     suite = ProfileTestSuite()
#     suite.addTests(tests)
#     return suite
