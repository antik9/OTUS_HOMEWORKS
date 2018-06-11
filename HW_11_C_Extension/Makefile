docker-build:
	docker build -t c_extension-hw_11 . \
		&& docker run --rm -it -p 8080:8080 c_extension-hw_11 /bin/bash

test:
	python setup.py test
