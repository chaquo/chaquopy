#!/bin/bash

# Set the path to the C++ library
export CTRANSLATE2_ROOT=$CHAQUOPY_LIB/ctranslate2-lib

pip install -r install_requirements.txt
python setup.py bdist_wheel
pip install dist/*.whl