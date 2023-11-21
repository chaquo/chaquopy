"""A lil' TOML parser."""

__all__ = ("loads", "load", "TOMLDecodeError")

# Chaquopy: backported from pip 21.2 to support TOML v1.0.0 syntax in pyproject.toml.
# See test_pep517_toml_1_0.
__version__ = "1.0.3"  # DO NOT EDIT THIS LINE MANUALLY. LET bump2version UTILITY DO IT

from pip._vendor.tomli._parser import TOMLDecodeError, load, loads
