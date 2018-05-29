## Multiprocessing Memcached Loader

This python program provide api for store values in memcached in special formatted gzip files.
These files consist information about installed devices. 

To up docker container with all dependencies within it run
```angular2html
make
```
By default it executes **make build_docker** in Makefile. 
It creates new image **hw_09_concurrency** and runs it interactively.

To run application you should have all **.tsv.gz** files in your running folder and 
then run
```angular2html
make start
```

If you want to run application with custom parameters you can choose them
from the following options:

```
-t --test (runs tests for the application)
-l --log (gets name of a logfile)
--dry (only logging available, no memcached load state)
--pattern (regexp pattern of file with support '*', like '*.tsv.gz')
--idfa (address of memcached for idfa keys)
--gaid (address of memcached for gaid keys)
--adid (address of memcached for adid keys)
--dvid (address of memcached for dvid keys)
-w --workers (number of workers for processing memcached load)
```

Example:
```angular2html
python memc_multi_load.py -l log.log --pattern './*.tsv.gz' \
    --idfa 127.0.0.1:11211 --workers 2
```

To test correctness of application logic you can run **tests.py** file:
```angular2html
python tests.py
```