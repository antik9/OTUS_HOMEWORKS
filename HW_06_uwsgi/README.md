## IP2W api (ip to weather)

To run ip2w api with uwsgi in Docker container run start.sh
```
./start.sh
```

In container run uwsgi service with
```
uwsgi --ini ip2w.ini
```

## Tests

To test api run uwsgi application and then run tests.py with python
```
python tests.py
```

## ip2w rpm package

Also you can install rmp package **ip2w-0.0.1-1.noarch.rpm** to your system and run api in daemon mode.
```
sudo rpm -i ip2w-0.0.1-1.noarch.rpm
```

To run system service
```
sudo service ip2w start
```

For correct work you should add location to your nginx.conf to proxy requests to ip2w socket
```
 location /ip2w/ 
 {
      include uwsgi_params;
      uwsgi_pass unix:/run/uwsgi/app.sock;
 }
 ```
