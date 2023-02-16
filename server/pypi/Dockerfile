FROM ubuntu:jammy

# persistent dependencies
RUN set -eux ; \
	apt-get -y update ; \
    apt-get -y --no-install-recommends install ca-certificates build-essential wget libncurses5 ;

# flang
RUN wget https://github.com/flang-compiler/flang/releases/download/flang_20190329/flang-20190329-x86-70.tgz ; \
    tar -xzvf *.tgz ; \
    rm -f *.tgz ; \
    ldconfig ;
