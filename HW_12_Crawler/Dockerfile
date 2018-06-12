FROM ubuntu:16.04

LABEL maintainer="Anton Illarionov"

RUN apt-get update \
  && apt-get install -y python3-pip python3-dev \
  && ln -s /usr/bin/python3 /usr/local/bin/python

RUN pip3 install aiohttp

ADD . /home/HW_12_Crawler

WORKDIR /home/HW_12_Crawler

EXPOSE 8080

ENTRYPOINT /bin/bash
