# -*- coding: utf-8 -*-

from twisted.internet.protocol import ClientFactory, Factory
from twisted.protocols import amp


class UserUnknown(Exception):
    pass


class RegisterUser(amp.Command):
    arguments = [
        ('mport', amp.Integer()),
    ]
    response = [
        ('mport', amp.Integer()),
    ]
    errors = {
        UserUnknown: 'user_unknown',
    }


class EchoServer(amp.AMP):

    @RegisterUser.responder
    def register(self, mport):
        print self.transport.getPeerCertificate().get_serial_number(), mport
        return {'mport': 9966}


class EchoServerFactory(Factory):

    protocol = EchoServer


class EchoClient(amp.AMP):
    pass


class EchoClientFactory(ClientFactory):

    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye!"
        from twisted.internet import reactor
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost - goodbye!"
        from twisted.internet import reactor
        reactor.stop()
