FROM centos:latest

LABEL maintainer="Anton Illarionov"

RUN yum install -y epel-release \
 && yum install -y nginx gcc wget curl screen vim git python-devel rpm-build \
 && curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" \
 && python get-pip.py \
 && rm get-pip.py \
 && pip install requests uwsgi

WORKDIR /home/
RUN echo
RUN git clone http://github.com/antik9/OTUS_HOMEWORKS

# Change nginx.conf
RUN mv /home/OTUS_HOMEWORKS/HW_06_uwsgi/nginx.conf /etc/nginx/nginx.conf \
 && cp /home/OTUS_HOMEWORKS/HW_06_uwsgi/server/config_ip2w.json /usr/local/etc/config_ip2w.json \
 && cp /home/OTUS_HOMEWORKS/HW_06_uwsgi/server/ip2w.py /usr/local/bin/ip2w.py \
 && touch /var/log/ip2w_py.log \
 && chmod a+w /var/log/ip2w_py.log \
 && mkdir /run/uwsgi

# Open 80 port from container
EXPOSE 80

WORKDIR /home/OTUS_HOMEWORKS/HW_06_uwsgi/server

ENTRYPOINT /usr/sbin/nginx \
 && /bin/bash 
