from setuptools import setup
from wheel.bdist_wheel import bdist_wheel


class BdistWheel(bdist_wheel):
    def run(self):
        pass


setup(
    name="bdist_wheel_fail_silently",
    version="1.0",
    cmdclass={"bdist_wheel": BdistWheel},
    packages=["bdist_wheel_fail_silently"]
)
