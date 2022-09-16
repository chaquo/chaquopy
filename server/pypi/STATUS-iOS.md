# Build status: iOS

## Working
chaquopy-freetype
chaquopy-libjpeg
chaquopy-libpng
chaquopy-libxml2
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
pynacl
pysha3
pywavelets
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
pycurl - needs chaquopy-curl
python-example - cmake failure
pyzbar - needs chaquopy-zbar
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
ta-lib - needs chaquopy-ta-lib
tensorflow - needs numpy on build host
tflite-runtime - numpy build problem; get_include()?
thinc - package definition problem
tokenizers - needs rust?
torch - needs numpy, chaquopy-libfortran, chaquopy-openblas
torchvision - needs torch
xgboost - CMake configuration problem
chaquopy-crc32c - cmake build... generates line noise in build
chaquopy-hdf5 - Source code no longer available?
chaquopy-libxslt - pulls in wrong libz
chaquopy-curl - configuration problem; pulls in macOS binaries
chaquopy-libiconv - configuration problem; pulls in macOS binaries
chaquopy-zbar - needs chaquopy-libiconv
chaquopy-geos - C++ linking issue
chaquopy-flac
chaquopy-libcxx
chaquopy-libffi - not needed; replaced with libffi from Python-Apple-support
chaquopy-libgfortran
chaquopy-libogg
chaquopy-libomp
chaquopy-libraw
chaquopy-libsndfile
chaquopy-libvorbis
chaquopy-libzmq
chaquopy-llvm
chaquopy-openblas
chaquopy-secp256k1
chaquopy-ta-lib
cmake-example




