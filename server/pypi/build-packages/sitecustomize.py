# distutils adds -I arguments for the build Python's include directory (and virtualenv include
# directory if applicable). Since we're using -idirafter for the target Python include (to
# enable building typed-ast), they will take priority no matter where they are on the command
# line. So we monkey-patch distutils to remove them.

from distutils import sysconfig
from distutils.command.build_ext import build_ext
import os
import sys


finalize_options_original = build_ext.finalize_options

def finalize_options_override(self):
    finalize_options_original(self)
    for item in [sysconfig.get_python_inc(),
                 sysconfig.get_python_inc(plat_specific=True),
                 os.path.join(sys.exec_prefix, 'include')]:
        try:
            self.include_dirs.remove(item)
        except ValueError:
            pass

build_ext.finalize_options = finalize_options_override


# Call the next sitecustomize script if there is one
# (https://nedbatchelder.com/blog/201001/running_code_at_python_startup.html).
del sys.modules["sitecustomize"]
this_dir = os.path.dirname(__file__)
path_index = sys.path.index(this_dir)
del sys.path[path_index]
try:
    import sitecustomize  # noqa: F401
finally:
    sys.path.insert(path_index, this_dir)
