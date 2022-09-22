import os
from setuptools import setup


setup(
    name="alpha",
    version="1.0",
    py_modules=[name.replace(".py", "")
                for name in os.listdir(".")
                if name.startswith("bravo")],
)
