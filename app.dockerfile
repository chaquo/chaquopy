FROM chaquopy-target

WORKDIR /root

COPY maven maven
COPY server/pypi/dist server/pypi/dist
COPY VERSION.txt ./
