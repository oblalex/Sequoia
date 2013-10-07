#!/usr/bin/env python
# -*- coding: utf-8 -*-

from OpenSSL import SSL
from twisted.internet import ssl, reactor
from twisted.internet.protocol import ClientFactory

from sequoia.protocol import EchoClient


class EchoClientFactory(ClientFactory):

    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye!"
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost - goodbye!"
        reactor.stop()


class CtxFactory(ssl.ClientContextFactory):

    def getContext(self):
        self.method = SSL.SSLv23_METHOD
        ctx = ssl.ClientContextFactory.getContext(self)
        ctx.use_certificate_file("sequoia/tests/auth/client.crt")
        ctx.use_privatekey_file("sequoia/tests/auth/client.key")
        return ctx


def main():
    factory = EchoClientFactory()
    reactor.connectSSL("localhost", 8000, factory, CtxFactory())
    reactor.run()

if __name__ == "__main__":
    main()
