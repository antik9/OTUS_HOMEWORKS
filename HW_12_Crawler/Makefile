build_docker:
	docker build -t hw_12_crawler .
	docker run --rm -it -p 8080:8080 hw_12_crawler

crawl:
	python crawler.py \
		--parsers 5 \
		--downloaders 10 \
		--basedir download \
		--logfile /var/log/ycomb.log

log:
	sudo touch /var/log/ycomb.log
	sudo chmod a+rw /var/log/ycomb.log
