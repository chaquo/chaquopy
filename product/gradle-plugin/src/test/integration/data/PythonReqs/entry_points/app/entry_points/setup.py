from setuptools import setup

setup(
    name="entry_points",
    version="0.0.1",
    entry_points={"console_scripts": ["hello = hello:main"]},
)
