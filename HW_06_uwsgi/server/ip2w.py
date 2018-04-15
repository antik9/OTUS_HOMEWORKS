import json
import requests
import logging
import os
import socket

from urllib.parse import quote

# -------------------------- Constants --------------------------- #


IPINFO_URL = "http://ipinfo.io/{ip_address}"
OPEN_WEATHER_URL = "http://api.openweathermap.org/data/2.5/weather?" \
                   "q={city},{country}&APPID={token}&lang=ru&units=metric"

TOKEN = os.environ.get("OPEN_WEATHER_TOKEN")

OK = 200
BAD_REQUEST = 400
BAD_GATEWAY = 502

ERRORS = {
    OK: "OK",
    BAD_REQUEST: "Bad Request",
    BAD_GATEWAY: "Bad Gateway",
}


# -------------------------- Exceptions -------------------------- #

class NoWeatherException(Exception):
    pass


# -------------------- Logging configuration --------------------- #

logging.basicConfig(format='[%(asctime)s] %(levelname)s %(message)s',
                    level=logging.INFO, datefmt='%Y.%m.%d %H:%M:%S')


# -------------------------- Weather api ------------------------- #

def application(env, start_response):
    """
    :param env: default parameter of wsgi, environment of request
    :param start_response: default wsgi function to make response
    :return: bytes array encoded in utf-8 with response data
    """
    ip_address = env["REQUEST_URI"].replace("/ip2w/", "")
    logging.info(env["REQUEST_METHOD"] + " " + env["REQUEST_URI"])

    if not (check_correct_url(ip_address)):
        return response_with_error(BAD_REQUEST,
                                   "Wrong format of ip {}".format(ip_address),
                                   start_response)
    try:
        city, country = get_geo(IPINFO_URL.format(ip_address=ip_address))
    except requests.exceptions.ConnectionError as e:
        logging.exception(e)
        return response_with_error(BAD_GATEWAY, "Cannot connect to IpInfo",
                                   start_response)

    if not (city and country):
        return response_with_error(BAD_REQUEST,
                                   "No city for ip {}".format(ip_address),
                                   start_response)

    try:
        temperature, conditions = \
            get_weather(OPEN_WEATHER_URL.format(city=quote(city),
                                                country=country,
                                                token=TOKEN))
    except NoWeatherException as e:
        logging.exception(e)
        return response_with_error(BAD_REQUEST,
                                   "No weather for ip {}".format(ip_address),
                                   start_response)

    except requests.exceptions.ConnectionError as e:
        logging.exception(e)
        return response_with_error(BAD_GATEWAY, "Cannot connect to OpenWeatherMap",
                                   start_response)

    start_response('200 OK', [('Content-Type', 'application/json')])
    return create_response(city=city,
                           temp=temperature,
                           conditions=conditions)


def check_correct_url(ip_address_):
    """
    :param ip_address_:
    :return: True if ip is correct, False otherwise
    """
    try:
        socket.inet_aton(ip_address_)
        return True
    except socket.error:
        return False


def get_geo(url):
    """
    :param url:
    :return: dictionary with information about city and country
    ip in url belongs to
    """
    geo_info = requests.get(url).json()
    return geo_info.get("city"), geo_info.get("country")


def get_weather(url):
    """
    :param url:
    :return: dictionary with information about temperature and weather
    conditions in city which passed in url
    """
    weather_info = requests.get(url).json()

    try:
        temperature = weather_info.get("main").get("temp")
        temperature = "{temp:+.2f}".format(temp=temperature)
        conditions = weather_info.get("weather")[0].get("description")

    except AttributeError:
        raise NoWeatherException

    return temperature, conditions


def create_response(**kwargs):
    """
    :param kwargs: kwargs dictionary depends on status code
    :return: list with data encoded in utf-8 to pass to response
    """
    logging.info("Response: " + json.dumps(kwargs))
    return [(json.dumps(kwargs, ensure_ascii=False) + "\n").encode("utf-8")]


def response_with_error(status_code, error, start_response):
    """
    :param status_code:
    :param error: Human readable error
    :param start_response: wsgi function
    :return: result of create_response function, bytes array with data encoded
    in utf-8 to pass in response
    """
    start_response('{status_code} {code_msg}'.format(status_code=status_code,
                                                     code_msg=ERRORS[status_code]),
                   [('Content-Type', 'application/json')])
    return create_response(error=error)
