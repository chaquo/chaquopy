# Be careful about what syntax and APIs are used in this file: it should give the
# correct error message on old Python versions going as far back as possible.

import sys


expected = sys.argv[1]
actual = "{}.{}".format(*sys.version_info[:2])
if actual != expected:
    # Our stderr will be appended to the message "$bpSetting is not a valid Python
    # $version command: ".
    sys.exit("it is version {}".format(actual))


# If any of the following things change, the build environment should be rebuilt.
# The Gradle plugin will use our stdout as a task input property.
for name in [
    "executable",  # In case the PATH changes, or the content of the directories on it.
    "base_prefix",  # In case a venv is recreated with a different copy of Python.
    "version",  # In case base_prefix is modified in place.
]:
    print("{}={!r}".format(name, getattr(sys, name)))
