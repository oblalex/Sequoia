# -*- coding: utf-8 -*-

import optparse
import sys

from twistar.registry import Registry
from twisted.enterprise import adbapi
from twisted.internet import reactor
from twisted.python import log

from sequoia.protocol import ServerClientsFactory, MediaProtocol
from sequoia.security import ServerContextFactory


def parse_args():
    usage = """usage: %prog --host=HOST --cport=CPORT --mport=MPORT"""
    parser = optparse.OptionParser(usage)

    help = "Host to run server on. Default: localhost"
    parser.add_option('--host', default='localhost', help=help)

    help = "Port for clients to connect to. Default: 0"
    parser.add_option('--cport', type='int', default=0, help=help)

    help = "Port for receiving media data. Default: 0"
    parser.add_option('--mport', type='int', default=0, help=help)

    options, args = parser.parse_args()
    return options.host, options.cport, options.mport


def show_connector_info(connector, description):
    info = connector.getHost()
    log.msg("{0} on {1}:{2}.".format(description, info.host, info.port))


def main():
    log.startLogging(sys.stdout)

    host, cport, mport = parse_args()

    Registry.DBPOOL = adbapi.ConnectionPool(
        'sqlite3', "sequoia/tests/auth/sequoia.db", check_same_thread=False)

    clients_factory = ServerClientsFactory()
    ctx_factory = ServerContextFactory(
        "sequoia/tests/auth/server.key",
        "sequoia/tests/auth/server.crt",
        "sequoia/tests/auth/root_ca.pem")

    clients_listener = reactor.listenSSL(cport, clients_factory, ctx_factory,
        interface=host)
    show_connector_info(clients_listener, "Listening clients")

    media_listener = reactor.listenUDP(mport, clients_factory.media_tx,
        interface=host)
    show_connector_info(media_listener, "Serving media")

    reactor.run()


if __name__ == "__main__":
    main()
