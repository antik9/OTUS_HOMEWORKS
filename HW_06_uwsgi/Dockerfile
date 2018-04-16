FROM centos:latest

LABEL maintainer="Anton Illarionov"

RUN yum install -y epel-release \
 && yum install -y nginx gcc wget curl screen vim git python-devel rpm-build \
 && curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" \
 && python get-pip.py \
 && rm get-pip.py \
 && pip install requests uwsgi

WORKDIR /home/
RUN git clone http://github.com/antik9/OTUS_HOMEWORKS

# Change nginx.conf
RUN mv /home/OTUS_HOMEWORKS/HW_06_uwsgi/nginx.conf /etc/nginx/nginx.conf \
 && mkdir /run/uwsgi

# Open 80 port from container
EXPOSE 80

WORKDIR /home/OTUS_HOMEWORKS/HW_06_uwsgi/server

ENTRYPOINT /usr/sbin/nginx \
 && /bin/bash 
