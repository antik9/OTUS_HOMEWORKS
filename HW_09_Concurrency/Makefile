build_docker:
	docker build -t hw_09_concurrency .
	docker run --rm -it \
		-p 13100:13100 \
		-p 13101:13101 \
		-p 13102:13102 \
		-p 13103:13103 \
		hw_09_concurrency

start:
	python memc_multi_load.py -l log.log \
		--idfa 127.0.0.1:13100 \
		--gaid 127.0.0.1:13101 \
		--adid 127.0.0.1:13102 \
		--dvid 127.0.0.1:13103 \
		--pattern "./*.tsv.gz" \
		--workers 8

move:
	for file in `ls -a | grep -E "^\..*\.gz"`; do \
		echo $$file; \
		new_file=`echo $$file | sed 's:^\.::'`; \
		mv $$file $$new_file; done