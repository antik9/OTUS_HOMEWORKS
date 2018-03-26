# Third Homework Task
## Python API to POST requests to work with scoring and interests of users

To start HttpServer you should type 
```
python3 api.py 
```
By default server is on 8080 port of your localhost and there is no log file, all log information goes to stdout.
If you want to change this configuration you can pass port and name of log file by their short and long options names like this:
```
python3 api.py -p 8989
python3 api.py --port 8989
python3 api.py -l log.log
python3 api.py --log log.log
```

To create valid requests to working server you should choose a method which would you like to use.
There are two methods: **clients_interests** and **online_score**.

## Common configuration to all requests

If you want to send request you should create POST request, for example by curl utilite, and send arguments and
parameters in **json** format.

For valid working of API pass next parameters with request:

* account
* login
* method 
* token
* arguments

## Clients interests

To get clients interests you should add ```"method": "clients_interests"``` to your json. Then you should add ids of
users in format of array in **arguments** parameter of your json. For example: ```"client_ids": [1, 2, 3]```. Also you can
add optional field **date** in format "DD.MM.YYYY". The whole request looks kinda
```
$ curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "admin",
"method": "clients_interests", "token":
"d3573aff1555cd67dccf21b95fe8c4dc8732f33fd4e32461b7fe6a71d83c947688515e36774c00fb630b039fe2223c991f045f13f2",
"arguments": {"client_ids": [1,2,3,4], "date": "20.07.2017"}}' http://127.0.0.1:8080/method/
```

## Online score

To get online score of user you want to know about you should add ```"method": "online_score"``` to your json. Then you
should add to arguments map such fields as

* phone ‐ string or number of length 11, starts with 7 (optional)
* email (optional)
* first_name (optional)
* last_name (optional)
* birthday ‐ date in format DD.MM.YYYY (optional)
* gender ‐ interer 0, 1, 2, where 0 is unknown, 1 is Male, 2 is Female (optional)

If you don't add one of pairs
* phone and email
* first_name and last_name
* birthday and gender
the request would not be valid. You should mention of these pairs.

The whole request looks kinda
```
curl -X POST -H "Content-Type: application/json" -d '{"account": "horns&hoofs", "login": "h&f",
"method": "online_score", "token":
"55cc9ce545bcd144300fe9efc28e65d415b923ebb6be1e19d2750a2c03e80dd209a27954dca045e5bb12418e7d89b6d718a9e35af3",
"arguments": {"phone": "79175002040", "email": "stupnikov@otus.ru", "first_name": "Stas",
"last_name": "Stupnikov", "birthday": "01.01.1990", "gender": 1}}' http://127.0.0.1:8080/method/
```
