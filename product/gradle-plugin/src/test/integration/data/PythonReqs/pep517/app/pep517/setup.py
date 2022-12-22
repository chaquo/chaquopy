import setuptools
from setuptools import setup

# See https://github.com/googleapis/python-crc32c/blob/main/tests/test___init__.py
import google_crc32c
assert google_crc32c.implementation == "c"
version = google_crc32c.value(b"\x00" * 32)

setup(
    name="pep517",
    version=version,
)
