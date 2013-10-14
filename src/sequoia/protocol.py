# -*- coding: utf-8 -*-

from twisted.internet.protocol import ClientFactory, Factory, DatagramProtocol
from twisted.protocols import amp
from twisted.python import log


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


class ServerProtocol(amp.AMP):

    @RegisterUser.responder
    def register(self, mport):
        print self.transport.getPeerCertificate().get_serial_number(), mport
        return {
            'mport': self.factory.get_media_port(),
        }


class ServerClientsFactory(Factory):

    protocol = ServerProtocol

    def __init__(self):
        self.media_tx = MediaProtocol()

    def get_media_port(self):
        return self.media_tx.transport.getHost().port


class ClientProtocol(amp.AMP):
    pass


class ClientFactory(ClientFactory):

    protocol = ClientProtocol

    def __init__(self):
        self.media_tx = MediaProtocol()

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye!"
        from twisted.internet import reactor
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost - goodbye!"
        from twisted.internet import reactor
        reactor.stop()


class MediaProtocol(DatagramProtocol):

    def __init__(self, address=None):
        # add codec and ciphers
        self.address = address
        self.buffer_in = ""
        self.buffer_out = ""

    def datagramReceived(self, data, address):
        if self.address is not None and address != self.address:
            log.msg("Message from unknown peer: {0}:{1}.".format(*address))
            return
        log.msg("Incoming {0} bytes from {1}:{2}.".format(len(data), *address))
