## IP2W api (ip to weather)

To run ip2w api with **uwsgi** in Docker container run start.sh
```
>>> ./start.sh
```

This application needed token for work with **openweathermap.org**. You should add token to your environment to **OPEN_WEATHER_TOKEN** variable
```
>>> OPEN_WEATHER_TOKEN={your_token}
>>> export OPEN_WEATHER_TOKEN
```

If you deploy this application on your local machine to run server you should change working directory to **server/**.</br>
In container you by default start at **server/**.</br>
Then you should run uwsgi service with
```
>>> uwsgi --ini ip2w.ini
```

## Tests

To test api, run uwsgi application and then run **tests.py** with python
```
>>> python tests.py
```

## ip2w rpm package

To build rpm package you should run **buildrpm.sh** in HW_06_uwsgi path
```
>>> bash buildrpm.sh ip2w.spec
```

To install rpm package on system run
```
>>> sudo rpm -i ip2w-0.0.1-1.noarch.rpm
```

To run system service
```
>>> sudo service ip2w start
```

For correct work you should add new location to your **nginx.conf** to proxy requests to ip2w socket
```
 location /ip2w/ 
 {
      include uwsgi_params;
      uwsgi_pass unix:/run/uwsgi/app.sock;
 }
 ```

## Requests

To make request to the service you can use curl utility.
```
>>> curl localhost:{your_nginx_port}/ip2w/46.48.185.235
{"city": "Yakutsk", "conditions": "ясно", "temp": "+4.00"}
```

