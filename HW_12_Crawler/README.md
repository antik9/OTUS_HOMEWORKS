## Python Crawler for news.ycombinator.com

This crawler is intended for downloading news from index page of ycombinator. 
It downloads content of links of top-30 news on index page and contents of all links in comments to that news.

To start crawler in docker container you can run make command:
```bash
>>> make
```

After that in system will be created new container and automatically it will be running.
To launch crawler with default parameters you can use another make command:
```bash
>>> make crawl
```

By default the crawler has refresh timeout 60 seconds, 5 parsers and 10 downloaders.

All parameters:

| Short opt | Long opt | Description |
|:---:|:---:|:---:|
| -p | --parsers | *number of parsers of html pages* |
| -d | --downloaders | *number of downloaders for http requests* |
| -l | --logfile | *name of logging file* |
| -t | --timeout | *timeout for http response* |
| -r | --refresh_timeout | *refresh news timeout* |
| -b | --basedir | *directory to store downloaded files* |

Example:
```bash
>>> python crawler.py -p 5 -d 10 -l /var/log/ycomb.log -t 10 -r 60 -b download
```
