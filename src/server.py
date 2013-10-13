# -*- coding: utf-8 -*-

import optparse

from twisted.internet import reactor

from sequoia.protocol import EchoServerFactory
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


def main():
    host, cport, mport = parse_args()

    factory = EchoServerFactory()
    ctx_factory = ServerContextFactory(
        "sequoia/tests/auth/server.key",
        "sequoia/tests/auth/server.crt",
        "sequoia/tests/auth/root_ca.pem")

    listener = reactor.listenSSL(cport, factory, ctx_factory, interface=host)
    host_info = listener.getHost()
    print "Listening clients on {host}:{port}.".format(
        host=host_info.host, port=host_info.port)

    reactor.run()


if __name__ == "__main__":
    main()
