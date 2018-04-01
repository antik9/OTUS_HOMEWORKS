__author__ = "Illarionov Anton"

import memcache
import time

# -------------------------- Constants --------------------------- #

HOUR = 60 * 60
DEFAULT_TRIALS = 3
TIMEOUT = 2     # seconds


# ------------------------- Exceptions --------------------------- #

class StorageError(Exception):
    """Basic exception for all errors in db connection"""
    pass


class StorageConnectionError(StorageError):
    pass


class StorageIsDeadError(StorageError):
    pass


class NoSuchElementError(StorageError):
    pass


# ------------------------ Storage class ------------------------- #


class Storage:
    """
    Class to establish connection to local/global memcached storage.
    By default Storage tries to connect to localhost on 11211 port,
    if connection fails for number of trials,
    """

    def __init__(self, address="localhost", port=11211, trials=10,
                 timeout=.1, alive_key="alive"):
        """Initialize connection and store some necessary information in self"""
        self.storage_address = str(address) + ":" + str(port)
        self.trials = trials
        self.alive = False
        self.timeout = timeout
        self.alive_key = alive_key

        # If connection is not alive raise Exception on __init__
        while not self.alive:
            self.connect_to_db()
            self.check_alive()
            if not self.alive:
                if self.trials:
                    self.trials -= 1
                    time.sleep(timeout)
                else:
                    raise StorageConnectionError("Cannot connect to storage")
            else:
                break

    def connect_to_db(self):
        """Unit function to perform connection to db"""
        self.connection = memcache.Client(servers=[self.storage_address],
                                          socket_timeout=TIMEOUT)

    def check_alive(self):
        """Unit to check is connection to memcached is alive"""
        self.alive = self.connection.set(self.alive_key, "1")

    def get(self, key, trials=DEFAULT_TRIALS):
        """
        Perform get request from memcached, raise Exception in case
        no such key in db or connection is dead
        """
        for _ in range(trials):
            self.check_alive()
            if not self.alive:
                self.connect_to_db()
            if self.alive:
                result = self.connection.get(key)
                if not result:
                    raise NoSuchElementError("key %s not in storage" % key[2:])
                return result
        raise StorageIsDeadError("Storage is dead!")

    def cache_get(self, key, trials=DEFAULT_TRIALS):
        """
        Cache get don't throw any Exceptions and return None in case
        there is no key in db ot connection is dead
        """
        try:
            return self.get(key, trials)
        except StorageError:
            return

    def __setkey(self, key, value, expire):
        """Method for testing"""
        self.connection.set(key, value, expire)

    def cache_set(self, key, value, expire=HOUR, trials=DEFAULT_TRIALS):
        """Cache set try to set key-value pair in memcached """
        for _ in range(trials):
            self.check_alive()
            if not self.alive:
                self.connect_to_db()
            if self.alive:
                self.connection.set(key, value, expire)
                return
