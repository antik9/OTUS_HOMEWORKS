#!/bin/python

import aiohttp
import asyncio
import async_timeout
import logging
import os
import re

from collections import deque
from datetime import datetime
from html import unescape
from optparse import OptionParser
from urllib.parse import quote

# *************** PATTERNS AND CONSTANTS *************** #

QUERY_LIMIT = 3
HOME_PAGE = 'https://news.ycombinator.com/'
COMMENT_PAGE = HOME_PAGE + 'item?id={id}'
COMMENT_FILE_NAME = '{:05d}.html'
HREF_PATTERN = re.compile(b'<(p|span).*<a[^>]*href="(?P<href>http[^"]+)"[^>]*>')
HEADER_PATTERN = re.compile(b'.*<[^>]*class="storylink"[^>]*>(?P<header>[^<]*)')
STORYLINK_PATTERN = re.compile(b'.*<a[^>]*class="storylink"[^>]*>.*')
LINK_PATTERN = re.compile(b'.*<a[^>]*href="(?P<link>[^"]*)"[^>]*class="storylink"[^>]*>.*')
ID_PATTERN = re.compile(b'.*id=\'up_(?P<id>\d+)\'.*')


# ********* CRAWLER CLASS WITH ASYNC HANDLERS ********** #

class Crawler:
    """
    Crawler class for https://news.ycombinator.com site.
    Crawler parse links of top 30 news on index page and parse links to
    comment for these news. Then it starts download all these pages to
    local system with appropriate news folder.
    """

    def __init__(self, queue, download_queue, opts):
        self.headers = deque(maxlen=30)         # Set for storing processed news
        self.queue = queue                      # Queue to communicate between fetcher/handlers
        self.download_queue = download_queue    # Queue to communicate between handlers/downloaders
        self.timeout = opts.timeout             # Timeout for asyncio wait for response
        self.refresh_timeout = opts.refresh_timeout  # Timeout for updating list of news
        self.basedir = opts.basedir             # Base directory to store downloaded files
        self.begin = datetime.now()             # Starting point of crawler
        self.ycomb_pages = 0                    # Processed pages from news.ycombinator source

    @staticmethod
    def get_dir_name_for_news(news):
        """
        Function to sub all not alphanumeric symbols from news to '_'
        """
        return re.sub(b'\W', b'_', news).decode('utf-8')

    @staticmethod
    async def fetch(session, url):
        """
        Returns html page for given url
        """
        async with session.get(url) as response:
            return await response.read()

    @staticmethod
    async def take_a_nap(how_long):
        """
        :param how_long: time of thread sleeping in seconds
        """
        await asyncio.sleep(how_long)

    def create_dir(self, news):
        """
        Create new directory for not processed news yet.
        Returns its relative name.
        """
        dir_name = os.path.join(self.basedir,
                                self.get_dir_name_for_news(news))
        os.makedirs(dir_name, exist_ok=True)
        return dir_name

    async def download_site(self):
        """
        Downloader for html files. Downloader get path to store and http url
        from self.download_queue to make request to get this page and store it
        on the local system.
        """
        while True:
            file_name, link = await self.download_queue.get()
            try:
                await self.write_to_file(file_name, link)
                logging.info("SUCCESS LINK {link}".format(link=link))
            except asyncio.TimeoutError:
                logging.exception("EXCEPTION timeout error for {link}".format(
                    link=link))
            except Exception:
                logging.exception("EXCEPTION unknown error for {link}".format(
                    link=link))
            finally:
                self.download_queue.task_done()

    async def get_comment_links(self, element_id, news_dir):
        """
        :param element_id: unique if of news
        :param news_dir: directory to store file
        to self.download_queue

        Function get page of news on news.ycombinator.com and pass html and news_dir
        to self.put_comment_links_to_queue to store links in self.download_queue
        """
        html = None
        self.wait_ycomb()
        try:
            async with async_timeout.timeout(self.timeout):
                async with aiohttp.ClientSession() as session:
                    html = await self.fetch(session,
                                            COMMENT_PAGE.format(id=element_id))
        except asyncio.TimeoutError:
            logging.exception("EXCEPTION timeout error for {link}".format(
                link=COMMENT_PAGE.format(id=element_id)))
        except Exception:
            logging.exception("EXCEPTION unknown error for {link}".format(
                link=COMMENT_PAGE.format(id=element_id)))

        if html:
            with open(os.path.join(news_dir, 'comments.html'), 'wb') as wfile:
                wfile.write(html)
            self.put_comment_links_to_queue(news_dir, html)

    def get_seconds(self):
        """
        Returns seconds passed from starting a crawler
        """
        return (datetime.now() - self.begin).total_seconds()

    async def get_top_news(self):
        """
        Function to get HOME_PAGE and parse news titles from it.
        Function put news that are not processed yet to self.queue
        """
        html = None
        try:
            async with async_timeout.timeout(self.timeout):
                async with aiohttp.ClientSession() as session:
                    html = await self.fetch(session, HOME_PAGE)
        except asyncio.TimeoutError:
            logging.exception("EXCEPTION timeout error for HOME_PAGE")
        except Exception:
            logging.exception("EXCEPTION unknown error for HOME_PAGE")

        if html:
            top_30 = re.findall(HEADER_PATTERN, html)
            new_top_news = set(top_30).difference(set(self.headers))
            self.headers.extend(new_top_news)
            if new_top_news:
                self.update_queue(html, new_top_news)

    @staticmethod
    def get_unescaped_link(href):
        """
        :param href: href link from <a> tag in comment on a page
        :return: unescaped and quoted link to make a request
        """
        href = unescape(href.decode('utf-8'))
        return 'https:' + quote(href[6:]) if href.startswith('https') \
            else 'http:' + quote(href[5:])

    async def handle_event(self):
        """
        Handler of http links stored in self.queue.
        Handler get http link, create new folder in system and parse all
        necessary links to download to which wiil be stored in self.download_queue
        """
        while True:
            news, link, element_id = await self.queue.get()
            logging.info('MAIN LINK: {}'.format(link))
            news_dir = self.create_dir(news)
            self.download_queue.put_nowait(
                (os.path.join(news_dir, 'index.html'), link))
            if element_id:
                await asyncio.ensure_future(
                    self.get_comment_links(element_id, news_dir))
            self.queue.task_done()

    def put_comment_links_to_queue(self, news_dir, html):
        """
        :param news_dir: directory to store file, should pass it in a tuple
        :param html: html text of response from the ycombinator news page

        Function retrieve all links from comments to news and pass'em to the
        self.download_queue
        """
        hrefs = re.findall(HREF_PATTERN, html)
        idx_file = 0
        for _, href in hrefs:
            if b'ycombinator' not in href:
                idx_file += 1
                href = self.get_unescaped_link(href)
                file_name = COMMENT_FILE_NAME.format(idx_file)
                self.download_queue.put_nowait((os.path.join(news_dir, file_name), href))
                logging.info('COMMENT LINK: {href} FILENAME: {file_name}'.format(
                    href=href, file_name=os.path.join(news_dir, file_name)))

    async def write_to_file(self, file_name, link):
        """
        Function to get http response and write it to the file
        """
        html = None
        async with async_timeout.timeout(self.timeout):
            async with aiohttp.ClientSession() as session:
                if not link.startswith('http'):
                    link = HOME_PAGE + link
                async with session.get(link) as response:
                    if link.endswith('pdf'):
                       file_name = file_name[:-4] + 'pdf'
                    with open(file_name, 'wb') as wfile:
                        logging.info("WRITING TO {}".format(file_name))
                        async for data, _ in response.content.iter_chunks():
                            wfile.write(data)

    def update_queue(self, html, new_top_news):
        """
        :param html: html page to parse links
        :new_top_news: news which are not downloaded yet

        Function add link for given top news to self.queue
        """
        links = re.findall(STORYLINK_PATTERN, html)
        for news in new_top_news:
            for link in links:
                if news in link:
                    try:
                        _link = re.search(LINK_PATTERN,
                                          link).group('link').decode('utf-8')
                        _match = re.search(ID_PATTERN, link)
                        element_id = _match.group('id').decode('utf-8') if _match \
                            else None
                        self.queue.put_nowait((news, _link, element_id))
                    except AttributeError:
                        logging.exception(
                            "EXCEPTION, cannot find link for {news}".format(
                                news=news))

    def wait_ycomb(self):
        """
        Resolve conflict with too much queris in a second to news.ycombinator.
        By default cannot take more than 3 query per second to ycombinator.
        """
        while True:
            if self.get_seconds() * QUERY_LIMIT > self.ycomb_pages:
                self.ycomb_pages += 1
                break
            self.take_a_nap(1)

    async def run_forever(self):
        """
        Infinite loop for crawler. After each iteration of exploring HOME_PAGE for
        new news thread sleeps for 60 seconds.
        """
        while True:
            logging.info("HEARTBEAT")
            asyncio.ensure_future(self.get_top_news())
            self.queue.join()
            await self.take_a_nap(self.refresh_timeout)


# ******************* MAIN PROCESS ******************** #

def main(opts):
    """
    :param opts: options from optparse
    Main function creates asyncio loop, asyncio tasks and Crawler instance.
    Then it starts all loops to process crawling.
    """
    loop = asyncio.get_event_loop()                 # Asyncio loop for async events
    queue = asyncio.Queue()                         # Queue for crawler class
    download_queue = asyncio.Queue()                # Qeueu for downloaders in crawler
    crawler = Crawler(queue, download_queue, opts)  # Crawler instance
    loop.create_task(crawler.run_forever())         # Tasks for asyncio loop
    for _ in range(opts.parsers):                   # Start parsers
        loop.create_task(crawler.handle_event())
    for _ in range(opts.downloaders):               # Start downloaders
        loop.create_task(crawler.download_site())
    loop.run_forever()
    loop.close()


if __name__ == "__main__":
    try:
        op = OptionParser()
        op.add_option("-p", "--parsers", action="store", type="int", default=3)
        op.add_option("-d", "--downloaders", action="store", type="int", default=5)
        op.add_option("-l", "--logfile", action="store", default=None)
        op.add_option("-t", "--timeout", action="store", type="int", default=30)
        op.add_option("-r", "--refresh_timeout", action="store", type="int", default=60)
        op.add_option("-b", "--basedir", action="store", default='download')
        (opts, args) = op.parse_args()
        logging.basicConfig(filename=opts.logfile, level=logging.INFO,
                            format='[%(asctime)s] %(levelname).1s %(message)s',
                            datefmt='%Y.%m.%d %H:%M:%S')
        logging.info("Start crawler of news.ycombinator")
        main(opts)
    except KeyboardInterrupt:
        print("\nUSER INTERRUPTION")
