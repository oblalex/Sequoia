#!/usr/bin/env python
# -*- coding: utf-8 -*-

from OpenSSL.SSL import Error as SSLError
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet import defer, reactor

from sequoia.protocol import ClientFactory, RegisterUser
from sequoia.security import ClientCtxFactory


def connect(host, port):

    def done(protocol):
        media_listener = reactor.listenUDP(0, factory.media_tx,
            interface=host)
        return protocol.callRemote(RegisterUser,
            mport=media_listener.getHost().port)

    def failed(err):
        err.trap(SSLError)
        return defer.fail(Exception("Invalid SSL credentials."))

    factory = ClientFactory()
    ctx_factory = ClientCtxFactory(
        "sequoia/tests/auth/client.key",
        "sequoia/tests/auth/client.crt")
    endpoint = SSL4ClientEndpoint(reactor, host, port, ctx_factory)
    d = endpoint.connect(factory)
    d.addCallbacks(done, failed)
    return d


def on_connection_success(result):
    print result


def on_connection_failed(reason):
    print "FAIL: %s" % reason.value


def main():
    d = connect("127.0.0.1", 8000)
    d.addCallbacks(on_connection_success, on_connection_failed)
    reactor.run()


if __name__ == "__main__":
    main()
