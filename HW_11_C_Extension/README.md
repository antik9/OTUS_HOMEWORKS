## C Extension for writing and reading protobuf devices for python2.7 

This extension give api for converting to protobuf and then write in gzip format specific devices.
Form of devices you can find in deviceapps.proto

To try this extension you can build docker container and run it in centos docker container.

You can create docker and run it interactively simply type
```
>>> make
```

After docker image has been built you can create new shared library and run tests on it by command:
```
>>> make test
```

The new library provides two functions:
* **deviceapps_xwrite_pb**
* **deviceapps_read_pb**
