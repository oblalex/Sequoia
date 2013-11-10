# -*- coding: utf-8 -*-

import optparse
import speex
import sys

from twistar.registry import Registry
from twisted.enterprise import adbapi
from twisted.internet import reactor
from twisted.python import log

from sequoia.media.media import AudioMixer
from sequoia.protocol import ServerClientsFactory, ServerMediaProtocol
from sequoia.security import ServerContextFactory


def parse_args():
    usage = """usage: %prog [--host=HOST] [--cport=CPORT] [--mport=MPORT]"""
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
    host, cport, mport = parse_args()

    Registry.DBPOOL = adbapi.ConnectionPool(
        'sqlite3', "sequoia/tests/auth/server_1/database.db",
        check_same_thread=False)

    mixer = AudioMixer()
    reactor.callWhenRunning(mixer.start)
    speexxx = None#speex.new()
    media_tx = ServerMediaProtocol(speexxx, mixer)
    clients_factory = ServerClientsFactory(media_tx)
    ctx_factory = ServerContextFactory(
        "sequoia/tests/auth/server_1/private_key.pem",
        "sequoia/tests/auth/server_1/certificate.pem",
        "sequoia/tests/auth/root/root_ca.crt")

    clients_listener = reactor.listenSSL(cport, clients_factory, ctx_factory,
        interface=host)
    show_connector_info(clients_listener, "Listening clients")
    media_listener = reactor.listenUDP(mport, media_tx,
        interface=host)
    show_connector_info(media_listener, "Serving media")

    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
