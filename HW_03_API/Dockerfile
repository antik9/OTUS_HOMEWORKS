FROM ubuntu:16.04

LABEL maintainer="Anton Illarionov"

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev memcached \
  && ln -s /usr/bin/python3 /usr/local/bin/python \
  && pip3 install --upgrade pip \
  && pip3 install python-memcached

ADD score_api /home/HW_03_API

WORKDIR /home/HW_03_API

ENTRYPOINT memcached -d -u root -p 11211 \
   && /bin/bash
