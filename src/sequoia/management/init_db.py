#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse
import sys

from twisted.enterprise import adbapi
from twisted.internet import reactor
from twistar.registry import Registry
from twisted.python import log


def parse_args():
    usage = """usage: %prog [--path=PATH]"""
    parser = optparse.OptionParser(usage)

    help = "Path to create database on. Default: sequoia.db"
    parser.add_option('--path', default='sequoia.db', help=help)

    options, args = parser.parse_args()
    return options.path


def init_db(txn):
    txn.execute("""CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        nick_name TEXT UNIQUE NOT NULL,
        sequence_number INTEGER NOT NULL DEFAULT 1
    )""")
    txn.execute("""CREATE TABLE media_encryption_keys(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sequence_number INTEGER NOT NULL,
        k1 TEXT NOT NULL,
        k2 TEXT NOT NULL,
        user_id INTEGER
    )""")

def on_error(err):
    log.err("An error occured: {err}.".format(err=err.value))

def main():
    path = parse_args()
    Registry.DBPOOL = adbapi.ConnectionPool(
        'sqlite3', path, check_same_thread=False)
    Registry.DBPOOL.runInteraction(
        init_db).addErrback(
        on_error).addBoth(
        lambda _: reactor.stop())
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
