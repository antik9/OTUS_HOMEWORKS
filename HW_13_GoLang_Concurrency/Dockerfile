FROM ubuntu:latest

LABEL maintainer="Anton Illarionov"

RUN apt-get update \
 && apt-get install -y golang git memcached netcat

RUN go get github.com/bradfitz/gomemcache/memcache \
 && go get github.com/golang/protobuf/proto

ADD . /home/HW13_Golang

WORKDIR /home/HW13_Golang

EXPOSE 13101 13102 13103 13104

ENTRYPOINT make \
 && /bin/bash
