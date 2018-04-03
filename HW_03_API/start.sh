#!/bin/bash

# Build new docker image and run it interactively with --rm flag
docker build -t otus_hw_03 .
docker run --rm -it -p 8080:8080 --net=host otus_hw_03
