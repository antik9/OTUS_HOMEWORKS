#!/bin/bash
set -x
set -e
yum clean all
yum install -y\
	git\
	make\
	gcc-c++\
	vim\
	ssh\
	screen

cd /opt
git clone https://github.com/python/cpython.git
cd cpython
git checkout 2.7
./configure --with-pydebug --prefix=/tmp/python
make -j2
