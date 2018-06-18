from setuptools import setup

setup(
    name="namespace_packages_a",
    version="1.0",
    packages=["pkg1", "pkg2", "pkg2.pkg21", "pkg3.pkg31"]
)
