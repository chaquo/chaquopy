#!/usr/bin/env python3

import os
from setuptools import setup

VERSION = os.environ["PKG_VERSION"]

# Since TensorFlow 2.0, tensorflow and tensorflow-gpu are identical
# (https://github.com/tensorflow/tensorflow/issues/39581). Rather than building two full-size
# wheels, we'll just make tensorflow-gpu depend on tensorflow.
setup(
    name="tensorflow-gpu",
    version=VERSION,
    install_requires=[f"tensorflow=={VERSION}"]
)
