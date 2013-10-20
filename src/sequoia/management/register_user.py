#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse
import random
import string
import sys

from OpenSSL import crypto
import simplejson as json
from twistar.registry import Registry
from twisted.enterprise import adbapi
from twisted.internet import defer, reactor
from twisted.python import log

import os, sys
sys.path.append(
    os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sequoia.models import User, MediaEncryptionKey


def parse_args():
    usage = """usage: %prog --db=DB --crt=CRT --nick=NICK --out=OUT"""
    parser = optparse.OptionParser(usage)

    help = "Path to database. Default: sequoia.db"
    parser.add_option('--db', default='sequoia.db', help=help)

    help = "Path to client's certificate. Default: client.crt"
    parser.add_option('--crt', default='client.crt', help=help)

    help = "Client's nick name."
    parser.add_option('--nick', help=help)

    help = "Path to output file. Default: media.keys"
    parser.add_option('--out', default='media.keys', help=help)

    options, args = parser.parse_args()

    if not options.nick:
        parser.error("Nick name is not specified.")

    return options.db, options.crt, options.nick, options.out


def get_serial_number(path):
    with open(path, 'r') as f:
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, f.read())
    return str(cert.get_serial_number())


def generate_key(length=32):
    return ''.join(random.choice(string.printable) for _ in range(length))


def generate_keys(start_number=1, count=5):
    return {x: (generate_key(), generate_key())
        for x in xrange(start_number, start_number+count)}


@defer.inlineCallbacks
def _register_user(txn, nick_name, serial_number):
    keys = generate_keys()
    saved_keys = []

    user = yield User(
        login=serial_number,
        nick_name=nick_name,
        sequence_number=1).save()

    for sequence_number, (k1, k2) in keys.items():
        key = yield MediaEncryptionKey(
            sequence_number=sequence_number, k1=k1, k2=k2).save()
        yield key.user.set(user)
        saved_keys.append(key)

    yield user.media_encryption_keys.set(saved_keys)
    defer.returnValue(keys)


def main():

    def on_error(err):
        log.err("An error occured: {err}.".format(err=err.value))

    def save_keys(keys):
        with open(out_path, 'w') as f:
            json.dump(keys, f, sort_keys=True, indent=4 * ' ')

    def register_user(txn, nick_name, serial_number):
        _register_user(txn, nick_name, serial_number).addCallback(
            save_keys).addErrback(
            on_error).addBoth(
            lambda _: reactor.stop())

    log.startLogging(sys.stdout)
    db_path, crt_path, nick_name, out_path = parse_args()
    serial_number = get_serial_number(crt_path)

    Registry.DBPOOL = adbapi.ConnectionPool(
        'sqlite3', db_path, check_same_thread=False)
    Registry.DBPOOL.runInteraction(register_user, nick_name, serial_number)
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
