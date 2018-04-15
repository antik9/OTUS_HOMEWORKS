import logging
import requests
import unittest

from ip2w import get_geo, check_correct_url, IPINFO_URL, OK, BAD_REQUEST, BAD_GATEWAY

logging.disable(logging.ERROR)


# ----------------------- Preload functions ------------------------ #

def cases(cases_):
    """Decorator to make tests in time of initialization"""

    def wrapper(func):
        def inner(*args):
            for case in cases_:
                new_args = args + (case if (isinstance(case, tuple)) else (case,))
                func(*new_args)

        return inner

    return wrapper


# --------------------------- Test class --------------------------- #

class TestAPI(unittest.TestCase):

    @cases([
        ("198.100.200.10", "Eden Prairie"),
        ("8.8.8.8", "Mountain View"),
        ("127.0.0.1", None)
    ])
    def test_correct_city(self, ip_address, city_correct):
        """Is returned city correct?"""
        city, country = get_geo(IPINFO_URL.format(ip_address=ip_address))
        self.assertEqual(city, city_correct)

    @cases([
        ("10.10.11.12", True),
        ("0.255.255.0", True),
        ("256.2.100.0", False),
        ("1.1.1.a2", False),
        ("100.1.1.1.1", False),
    ])
    def test_correct_url(self, ip_address, bool_value):
        """Is ip checked correctly?"""
        self.assertEqual(check_correct_url(ip_address), bool_value)

    @cases([
        "198.100.200.10",
        "8.8.8.8",
    ])
    def test_functional_good_ip(self, url):
        """Is API response correct?"""
        response = requests.get("http://localhost:80/ip2w/{url}".format(url=url))
        if response.status_code != BAD_GATEWAY:
            print("\nGATEWAY is OK")
            self.assertEqual(response.status_code, OK)
            content = response.json()
            self.assertEqual(len(content), 3)
            self.assertTrue(content.get("temp"))
            self.assertTrue(content.get("city"))
        else:
            print("\nGATEWAY is RESET BY PEER")

    @cases([
        "127.0.0.1",
        "0.0.0.0",
    ])
    def test_functional_bad_ip(self, url):
        """Is API bad response correct?"""
        response = requests.get("http://localhost:80/ip2w/{url}".format(url=url))
        self.assertEqual(response.status_code, BAD_REQUEST)
        self.assertEqual(response.json().get("error"),
                         "No city for ip {}".format(url))


if __name__ == "__main__":
    unittest.main()
