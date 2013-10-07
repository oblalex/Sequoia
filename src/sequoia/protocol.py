# -*- coding: utf-8 -*-
from twisted.internet.protocol import Protocol


class EchoServer(Protocol):

    def dataReceived(self, data):
        self.transport.write(data)

class EchoClient(Protocol):

    def connectionMade(self):
        print "hello, world"
        self.transport.write("hello, world!")

    def dataReceived(self, data):
        print "Server said:", data
        self.transport.loseConnection()
