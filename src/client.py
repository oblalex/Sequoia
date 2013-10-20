#!/usr/bin/env python
# -*- coding: utf-8 -*-

import optparse
import simplejson as json
import sys

from OpenSSL.SSL import Error as SSLError
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet import defer, reactor
from twisted.python import log

from sequoia.protocol import ClientFactory, RegisterUser
from sequoia.security import ClientCtxFactory


def parse_args():
    usage = """usage: %prog [--host=HOST] --port=PORT --key=KEY --crt=CRT --media_keys=MEDIA_KEYS"""
    parser = optparse.OptionParser(usage)

    help = "Server's host. Default: localhost"
    parser.add_option('--host', default='localhost', help=help)

    help = "Server's port."
    parser.add_option('--port', type='int', help=help)

    help = "Path to private key. Default: client.key"
    parser.add_option('--key', default='client.key', help=help)

    help = "Path to certificate. Default: client.crt"
    parser.add_option('--crt', default='client.crt', help=help)

    help = "Path to media keys. Default: media.keys"
    parser.add_option('--media_keys', default='media.keys', help=help)

    options, args = parser.parse_args()
    if not options.port:
        parser.error("Server's port is not specified.")
    if not options.key:
        parser.error("Path to private key is not specified.")
    if not options.crt:
        parser.error("Path to private certificate is not specified.")
    if not options.media_keys:
        parser.error("Path to media keys is not specified.")

    return (options.host, options.port, options.key, options.crt,
        options.media_keys, )


def main():
    host, port, key, crt, media_keys = parse_args()

    def connect():

        def done(protocol):
            d = factory.media_tx.on_start
            m_listener = reactor.listenUDP(0, factory.media_tx, interface=host)
            return d.addCallback(lambda _: protocol.callRemote(
                RegisterUser, mport=m_listener.getHost().port))

        def failed(err):
            err.trap(SSLError)
            return defer.fail(Exception("Invalid SSL credentials."))

        factory = ClientFactory()
        ctx_factory = ClientCtxFactory(key, crt)
        endpoint = SSL4ClientEndpoint(reactor, host, port, ctx_factory)
        d = endpoint.connect(factory)
        d.addCallbacks(done, failed)
        return d

    def on_connection_success(result):
        print result['mport']
        print result['self_nick']
        print result['participants']
        print keys[str(result['keys_pair'])]

    def on_connection_failed(reason):
        print "FAIL: %s" % reason.value
        reactor.stop()

    with open(media_keys, 'r') as f:
        keys = json.loads(f.read())

    d = connect()
    d.addCallbacks(on_connection_success, on_connection_failed)
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
