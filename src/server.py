# -*- coding: utf-8 -*-

from OpenSSL import SSL
from twisted.internet import ssl, reactor
from twisted.internet.protocol import Factory

from sequoia.protocol import EchoServer


def verifyCallback(connection, x509, errnum, errdepth, ok):
    if not ok:
        print "invalid cert from subject:", x509.get_subject()
        return False
    else:
        print "Certs are fine"
    return True


def main():
    factory = Factory()
    factory.protocol = EchoServer

    myContextFactory = ssl.DefaultOpenSSLContextFactory(
        "sequoia/tests/auth/server.key", "sequoia/tests/auth/server.crt")

    ctx = myContextFactory.getContext()
    ctx.set_verify(
        SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
        verifyCallback)
    ctx.load_verify_locations("sequoia/tests/auth/root_ca.pem")

    reactor.listenSSL(8000, factory, myContextFactory)
    reactor.run()


if __name__ == "__main__":
    if __package__ is None:
        from os import sys, path
        sys.path.append(path.dirname(path.abspath(__file__)))
    main()
