import collections
import datetime
import gzip
import hashlib
import os
import unittest

from multiprocessing import Array, JoinableQueue, Lock, Process, Manager

import appsinstalled_pb2

from memc_multi_load import produce, process_file, parse_appsinstalled


# *************** HELPER CLASSES **************** #

class MockMem:
    """
    Mocking class of python memcache library
    """

    @staticmethod
    class Client:
        """
        Class for storing values in runtime
        """

        def __init__(self, storage):
            self.storage = storage[0]

        def set_multi(self, package):
            """
            :param package: python dict to store
            Function update storage of client,
            analogue of memcached store key-value pairs
            """
            self.storage.update(package)
            return []


# **************** TEST CLASSES ***************** #

class TestLoad(unittest.TestCase):

    def setUp(self):
        self.lines = [
            "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n",
            "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
        ]
        self.filename = hashlib.sha224(
            str(datetime.datetime.now()).encode('utf8')).hexdigest() + '.tsv.gz'

        # Write to temporary file
        with gzip.open(self.filename, 'wt') as gzip_file:
            for line in self.lines:
                gzip_file.write(line)

    @staticmethod
    def parse_value(line):
        appsinstalled = parse_appsinstalled(line)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        ua.apps.extend(appsinstalled.apps)
        return ua.SerializeToString()

    # ------------------ TESTS ------------------- #

    def test_functional(self):
        """ Load to mock database """
        manager = Manager()
        device_memc = {
            "idfa": manager.dict(),
            "gaid": manager.dict(),
            "adid": manager.dict(),
            "dvid": manager.dict(),
        }

        options = collections.namedtuple('options', ['pattern', 'dry', 'log'])
        options.pattern = self.filename
        options.dry = False
        options.log = None

        # Create primitives for intercommunication
        lock = Lock()
        file_stats = Array(typecode_or_type='i', size_or_initializer=2)

        # Memcached clients
        memc_clients = dict((key, MockMem.Client([address]))
                            for key, address in device_memc.items())

        # Create Queue for implementing producer -> consumer communication
        io_queue = JoinableQueue()

        # Start consumer processes
        workers = []
        p = Process(target=process_file, args=(io_queue, file_stats,
                                               device_memc, memc_clients,
                                               options, lock))
        p.start()
        workers.append(p)

        # Start producer process
        produce(io_queue, options, workers, file_stats)

        self.assertIsNotNone(memc_clients['gaid'].storage.get('gaid:7rfw452y52g2gq4g'))
        self.assertIsNotNone(memc_clients['idfa'].storage.get('idfa:1rfw452y52g2gq4g'))
        self.assertEqual(memc_clients['gaid'].storage.get('gaid:7rfw452y52g2gq4g'),
                         self.parse_value(self.lines[1]))
        self.assertEqual(memc_clients['idfa'].storage.get('idfa:1rfw452y52g2gq4g'),
                         self.parse_value(self.lines[0]))

    def tearDown(self):
        os.remove('.' + self.filename)


loader = unittest.TestLoader()
suite = unittest.TestSuite()
a = loader.loadTestsFromTestCase(TestLoad)
suite.addTest(a)


class NewResult(unittest.TextTestResult):
    def getDescription(self, test):
        doc_first_line = test.shortDescription()
        return doc_first_line or ""


class NewRunner(unittest.TextTestRunner):
    resultclass = NewResult


runner = NewRunner(verbosity=2)
runner.run(suite)
