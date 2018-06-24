## Golang Memcached Loader

This program provide api for storing values in memcached in special formatted gzip files.
These files consisted of information about installed devices. 

To up docker container with all dependencies within it run 
```angular2html
>>> make docker
```
By default it executes **docker build -t hw_13_golang .** in Makefile. 
It creates new image **hw_13_golang** and runs it interactively.

To run application you should have all **.tsv.gz** files in folder **tsv/** or provide 
your folder by passing appropriate argument in command line and then run:
```angular2html
>>> make run || ./MemcLoad
```

If you want to run application with custom parameters you can choose them
from the following options:

```
-log (gets name of a logfile)
-path (path of analyzing files)
-idfa (address of memcached for idfa keys)
-gaid (address of memcached for gaid keys)
-adid (address of memcached for adid keys)
-dvid (address of memcached for dvid keys)
-workers (number of workers for processing memcached load)
```

Example:
```angular2html
./MemcLoad -log=MemcLoad.log -path=tsv \
    -idfa="127.0.0.1:11211" -workers=2
```
