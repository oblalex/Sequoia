# -*- coding: utf-8 -*-
from twisted.internet.protocol import ClientFactory, Factory, Protocol


class EchoServer(Protocol):

    def dataReceived(self, data):
        print self.transport.getPeerCertificate().get_serial_number()
        self.transport.write(data)


class EchoServerFactory(Factory):

    protocol = EchoServer


class EchoClient(Protocol):

    def connectionMade(self):
        print "hello, world"
        self.transport.write("hello, world!")

    def dataReceived(self, data):
        print "Server said:", data
        self.transport.loseConnection()


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
