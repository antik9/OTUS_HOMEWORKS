#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import glob
import gzip
import logging
import os
import sys

from itertools import islice
from multiprocessing import Array, JoinableQueue, Lock, Process
from optparse import OptionParser

import appsinstalled_pb2
import memcache

# ******************** CONSTANTS ******************* #

AppsInstalled = collections.namedtuple(
    "AppsInstalled",
    ["dev_type", "dev_id", "lat", "lon", "apps"]
)

NORMAL_ERR_RATE = 0.01
PACKAGE_SIZE = 400


# ******************** FUNCTIONS ******************* #

def dot_rename(path):
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


def insert_appsinstalled(app_type, memc_client, apps, dry_run=False):
    """
    :param app_type: type of app device in processed file
    :param memc_client: memcached connection client appropriate to app_type
    :param apps: apps information to store in memcached
    :param dry_run: if dry_run is True memcached load is idle, only logging is up
    :return: number of keys which have not loaded to memcached

    Function creates key-value pairs and store them in memcached. It gets
    only one app_type information and appropriate memcached client.
    """

    package, log_package = {}, []

    # Process apps and create key, value pairs
    for appsinstalled in apps:
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)

        if dry_run:
            log_package.append((key, ua))
        else:
            packed = ua.SerializeToString()
            package.update({key: packed})

    # Loading or only logging
    if dry_run:
        for key, ua in log_package:
            logging.debug("%s - %s -> %s" %
                          (app_type, key, str(ua).replace("\n", " ")))
    else:
        try:
            return len(memc_client.set_multi(package))
        except Exception as e:
            logging.exception("Cannot write to memc %s: %s" % (app_type, e))
            return len(apps)


def parse_appsinstalled(line):
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
        logging.info("Not all user apps are digits: `%s`" % line)
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        logging.info("Invalid geo coords: `%s`" % line)
    return AppsInstalled(dev_type, dev_id, lat, lon, apps)


def process_file(io_queue, file_stats, device_memc, memc_clients, options, lock):
    """
    :param io_queue: multiprocessing.Queue to communicate with producer
    :param file_stats: multiprocessing.Array with value [errors, processed lines]
    :param device_memc: memcached addresses for storing values
    :param memc_clients: dictionary with memcached Clients for each app device
    :param options: options from OptionsParser
    :param lock: multiprocessing.Lock for changing file_stats

    Function start process which get packages of string from queue, parse them
    and store them in memcached in the appropriate device (device_memc)
    """

    # Call basic config for new process, cause it doesn't inherit configuration
    # from the parent
    logging.basicConfig(filename=options.log,
                        level=logging.INFO if not options.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')

    # Handle packages with strings for adding values to memcached
    while True:
        package = io_queue.get()
        errors, processed = 0, 0
        apps = dict((app_type, []) for app_type in device_memc)

        for line in package:
            appsinstalled = parse_appsinstalled(line)

            if not appsinstalled:
                errors += 1
                continue

            if apps.get(appsinstalled.dev_type) is None:
                errors += 1
                continue

            apps[appsinstalled.dev_type].append(appsinstalled)

        for app_type, _apps in apps.items():
            if not _apps:
                continue
            _errors = insert_appsinstalled(app_type, memc_clients[app_type], _apps, options.dry)
            processed += len(_apps) - _errors
            errors += _errors

        with lock:
            file_stats[0] += errors
            file_stats[1] += processed

        io_queue.task_done()


def produce(io_queue, options, workers, file_stats):
    """
    :param io_queue: multiprocessing.Queue to communicate with producer
    :param options: options from OptionsParser
    :param workers: number of isolated consumers which load values to memcached
    :param file_stats: multiprocessing.Array with value [errors, processed lines]

    The function is reading content of the files which satisfy pattern options.pattern
    and send packages of strings to io_queue.
    When work is done func produce terminates consumers processes.
    """

    # Iterate through appropriate files defined by pattern in options.patterns
    for fn in sorted(glob.iglob(options.pattern)):

        logging.info('Processing %s' % fn)
        fd = gzip.open(fn, 'rt')

        package = list(islice(fd, PACKAGE_SIZE))
        while package:
            io_queue.put(package)
            package = list(islice(fd, PACKAGE_SIZE))

        io_queue.join()

        if not file_stats[1]:
            file_stats[0], file_stats[1] = 0, 0
            fd.close()
            dot_rename(fn)
            continue

        err_rate = file_stats[0] / file_stats[1]
        file_stats[0], file_stats[1] = 0, 0

        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" %
                          (err_rate, NORMAL_ERR_RATE))
        fd.close()
        dot_rename(fn)

    # Terminate all workers which have done the work
    for worker in workers:
        worker.terminate()


def main(options):
    """
    :param options: options from OptionsParser

    Function start several processes (number of which defined in options.workers)
    and creates multiprocessing array and lock for further communication between
    all processes of the program.
    """

    # Get addresses of memcached for each kind of devices
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    # Create primitives for intercommunication
    lock = Lock()
    file_stats = Array(typecode_or_type='i', size_or_initializer=2)

    # Memcached clients
    memc_clients = dict((key, memcache.Client([address]))
                        for key, address in device_memc.items())

    # Create Queue for implementing producer -> consumer communication
    io_queue = JoinableQueue()

    # Start consumer processes
    workers = []
    for i in range(options.workers):
        p = Process(target=process_file, args=(io_queue, file_stats,
                                               device_memc, memc_clients,
                                               options, lock))
        p.start()
        workers.append(p)

    # Start producer process
    produce(io_queue, options, workers, file_stats)


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\n" \
             "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    op.add_option("-w", "--workers", action="store", type="int", default=1)
    (opts, args) = op.parse_args()

    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
