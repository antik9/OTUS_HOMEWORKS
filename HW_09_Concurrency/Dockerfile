FROM ubuntu:16.04

LABEL maintainer="Anton Illarionov"

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev memcached \
  && ln -s /usr/bin/python3 /usr/local/bin/python

RUN pip3 install python-memcached protobuf

ADD . /home/HW_09_Concurrency

WORKDIR /home/HW_09_Concurrency

EXPOSE 13100 13101 13102 13103

ENTRYPOINT memcached -d -u root -p 13100 \
  && memcached -d -u root -p 13101 \
  && memcached -d -u root -p 13102 \
  && memcached -d -u root -p 13103 \
  && /bin/bash