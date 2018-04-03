#!/bin/bash

# Build new docker image and run it interactively with --rm flag
docker build -t otus_hw_03 .
docker run --rm -it otus_hw_03
