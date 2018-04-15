#!/bin/bash

docker build -t otus_hw_06_api .
docker run --rm -it -p 8080:80 otus_hw_06_api
