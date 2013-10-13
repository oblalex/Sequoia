#!/usr/bin/env python
# -*- coding: utf-8 -*-

from OpenSSL.SSL import Error as SSLError
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet import defer, reactor

from sequoia.protocol import EchoClientFactory, RegisterUser
from sequoia.security import ClientCtxFactory


def connect(host, port):

    def done(protocol):
        return protocol.callRemote(RegisterUser, mport=9988)

    def failed(err):
        err.trap(SSLError)
        return defer.fail(Exception("Invalid SSL credentials."))

    factory = EchoClientFactory()
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
