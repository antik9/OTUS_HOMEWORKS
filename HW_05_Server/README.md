# HTTP server which handles GET and HEAD requests

Thre kernal of the server is thread pool. On launch server starts several threads with sockets with SO_REUSEADDR flag. 
Each socket handles connections one by one until the server will manually stop.

## Configuration
To start server you need to launch it with **python3**.
The server provides some tweeks of configutaion.
You can pass next parameters to it:

```
-l --log (logfile, by default=stdin)
-p --port (port, by default=8000)
-w --workers (number of threads which handle connections by default=2)
-r --root_dir (root directory of files which you want to provide, by default=/httptest)
```
The example of start server
```
python3 httpd.py -w 10 -p 8000 -l log2018_08_04.log -r /httptest
```

## Docker launch

If you want to start server in docker container you should launch start.sh file.
```
bash start.sh
```
After this command docker builds new image called otus_hw_05 and launch it with --rm -it parameters.
The image foundation is centos:latest.
When the command lime provides you access to container you can start server in it by this command:
```
python3.6 httpd.py
```

## Tests
To run tests on server you can launch httptest.py file:
```
python3 httptest.py
python3.6 httptest.py
```

## Benchmarking

Characteristics of processor.
```
product:  Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
vendor:   Intel Corp.
version:  Intel(R) Core(TM) i7-7700HQ CPU @ 2.80GHz
size:     3612MHz
capacity: 4005MHz
```

Server benchmarking made by apache benchmark command:
```
ab -n 50000 -c 100 -r http://localhost:9090/httptest/test.html
```

Result:

```
Server Software:        GetAndHeadServer
Server Hostname:        localhost
Server Port:            8000

Document Path:          /httptest/test.html
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   11.996 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      9000000 bytes
HTML transferred:       1700000 bytes
Requests per second:    4167.93 [#/sec] (mean)
Time per request:       23.993 [ms] (mean)
Time per request:       0.240 [ms] (mean, across all concurrent requests)
Transfer rate:          732.64 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.3      0       9
Processing:     4   24   1.3     24      34
Waiting:        4   24   1.3     24      34
Total:         13   24   1.3     24      38

Percentage of the requests served within a certain time (ms)
  50%     24
  66%     24
  75%     25
  80%     25
  90%     26
  95%     26
  98%     27
  99%     27
 100%     38 (longest request)
```
