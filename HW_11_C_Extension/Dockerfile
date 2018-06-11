FROM centos:latest

LABEL maintainer = "Anton Illarionov"

RUN set -xe \
  && yum install -y  gcc \
    zlib-devel \
	make \
	protobuf \
	protobuf-c \
	protobuf-c-compiler \
	protobuf-c-devel \
	python-devel \
	python-setuptools \
	gdb 

ADD . /tmp/otus

EXPOSE 8080

WORKDIR /tmp/otus

ENTRYPOINT ulimit -c unlimited \
  && protoc-c --c_out=. deviceapps.proto \
  && /bin/bash
