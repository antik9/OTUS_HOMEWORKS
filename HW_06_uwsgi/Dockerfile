FROM centos:latest

LABEL maintainer="Anton Illarionov"

ENV OPEN_WEATHER_TOKEN=35ee6b3244899f265cdbebde58d053f9

# Install python3 and other utilities to work with
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y nginx gcc wget curl screen vim git \
 python36u python36u-devel.x86_64

# Create virtualenv for py3
RUN python3.6 -m venv /home/py36
RUN /home/py36/bin/pip3 install requests uwsgi

# Add current folder to container
ADD . /home/HW_06_api
WORKDIR /home/HW_06_api/server

# Change nginx.conf
RUN mv /home/HW_06_api/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /run/uwsgi

# Open 80 port from container
EXPOSE 80

ENTRYPOINT /usr/sbin/nginx \
 && /bin/bash 
# && source /home/py36/bin/activate 

