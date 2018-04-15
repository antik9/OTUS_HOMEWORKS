FROM centos:latest

LABEL maintainer="Anton Illarionov"

RUN yum install -y epel-release
RUN yum install -y nginx gcc wget curl screen vim git python-devel rpm-build
RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
RUN python get-pip.py
RUN rm get-pip.py 
RUN pip install requests uwsgi

WORKDIR /home/
RUN git clone http://github.com/antik9/OTUS_HOMEWORKS
WORKDIR /home/OTUS_HOMEWORKS/HW_06_uwsgi

# Change nginx.conf
RUN mv /home/OTUS_HOMEWORKS/HW_06_uwsgi/nginx.conf /etc/nginx/nginx.conf
RUN mkdir /run/uwsgi

# Open 80 port from container
EXPOSE 80

ENTRYPOINT /usr/sbin/nginx \
 && /bin/bash 

