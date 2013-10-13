#!/usr/bin/env python
# -*- coding: utf-8 -*-

from OpenSSL.SSL import Error as SSLError
from twisted.internet import reactor

from sequoia.protocol import EchoClientFactory
from sequoia.security import ClientCtxFactory


def main():
    factory = EchoClientFactory()
    ctx_factory = ClientCtxFactory(
        "sequoia/tests/auth/client.key",
        "sequoia/tests/auth/client.crt")
    try:
        reactor.connectSSL("localhost", 8000, factory, ctx_factory)
    except SSLError:
        print "Invalid SSL credentials."
    else:
        reactor.run()


if __name__ == "__main__":
    main()
