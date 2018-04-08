FROM centos:latest

LABEL maintainer="Anton Illarionov"

RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u
RUN yum install -y httpd24u-tools-2.4.29-1.ius.centos7.x86_64

ADD server /home/HW_05_Server

WORKDIR /home/HW_05_Server

ENTRYPOINT /bin/bash
