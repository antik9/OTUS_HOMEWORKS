all: up
	go build MemcLoad.go

run:
	./MemcLoad

up:
	for i in 13101 13102 13103 13104; do memcached -u root -d -p $$i; done;

clean:
	for i in 13101 13102 13103 13104; do echo 'flush_all' | nc localhost $$i; done;

docker:
	docker build -t hw13_golang .
	docker run --rm -it -p 13101:13101 -p 13102:13102 -p 13103:13103 -p 13104:13104 hw13_golang
