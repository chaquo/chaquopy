# Build status: iOS

## Working
chaquopy-freetype
chaquopy-libjpeg
chaquopy-libogg
chaquopy-libpng
chaquopy-libxml2
chaquopy-libiconv
chaquopy-curl
chaquopy-ta-lib
chaquopy-zbar
cffi
numpy
aiohttp
argon2-cffi
bcrypt
backports-zoneinfo
bitarray
brotli
cryptography
cymem
cytoolz
editdistance
ephem
frozenlist
greenlet
kiwisolver
lru-dict
matplotlib
multidict
murmurhash
netifaces
pillow
preshed
pycrypto
pycurl
pynacl
pysha3
pywavelets
pyzbar
regex
ruamel-yaml-clib
scandir
srsly
spectrum
twisted
typed-ast
ujson
wordcloud
yarl
zstandard

## Known problems

blis - no idea...
coincurve needs chaquopy-secp256k1
cvxopt - needs chaquopy-openblas
dlib - needs chaquopy-openblas
gensim - numpy buildsystem problem
gevent - needs greenlet; issue with inline libev configure
google-crc32c - needs chaquopy-crc32
grpcio - Unknown; failed during build
h5py - needs chaquopy-hdf5
llvmlite - needs chaquopy-llvm
lxml - needs chaquopy-libxml2, chaquopy-libxslt
numba - needs numpy; fails due to a config-reading process needing npymath
opencv-contrib-python
opencv-contrib-python-headless
opencv-python
opencv-python-headless
pandas - needs numpy; fails trying to import numpy during setup
psutil - doesn't make any sense on iOS?
pycares - missing ares_config.h?
pycryptodome - possible configuration problem; binary artefacts aren't consistent between platforms
pycryptodomex - possible configuration problem; binary artefacts aren't consistent between platforms
python-example - cmake failure
pyzmq - needs chaquopy-libzmq
rawpy - subrepo cloning failure?
rpi-gpio - does this make any sense? Fails build due to missing sys/epoll.h
scikit-image - needs numpy; numpy configuration problem
scikit-learn - needs numpy, scipy, chaquopy-openblas
scipy - needs numpy; can't find at build time
sentencepiece - cmake build failure
shapely - needs chaquopy-geos
soundfile - needs chaquopy-libsndfile
spacy - needs srsly, blis
statsmodels - cythonize problem
ta-lib - needs chaquopy-ta-lib, numpy
tensorflow - needs numpy on build host
tflite-runtime - numpy build problem; get_include()?
thinc - package definition problem
tokenizers - needs rust?
torch - needs numpy, chaquopy-libfortran, chaquopy-openblas
torchvision - needs torch
xgboost - CMake configuration problem
chaquopy-crc32c - cmake build... generates line noise in build
chaquopy-hdf5 - Source code no longer available?
chaquopy-libxslt - issue with iconv linkage from libxml?
chaquopy-geos - C++ linking issue
chaquopy-flac - linking problem with missing symbols
chaquopy-libcxx - makes some assumptions about how the toolchain directory is laid out
chaquopy-libffi - not needed; replaced with libffi from Python-Apple-support
chaquopy-libgfortran - Needs a fortran compiler.
chaquopy-libomp - Isn't a build; copies a file from the Android toolchain
chaquopy-libraw - Checks for modified autoconf files, asks for aclocal-1.15
chaquopy-libsndfile - needs chaquopy-flac
chaquopy-libvorbis - build fails; uint16_t not recognized on x86_64
chaquopy-libzmq - linking problem with missing symbols. Likely needs an update to configure to add flags for iOS
chaquopy-llvm - Needs cmake
chaquopy-openblas - needs chaquopy-libfortran
chaquopy-secp256k1 - No tarball, so config.sub is generated, but needs patching.

cmake-example - Needs Cmake

