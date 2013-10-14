# -*- coding: utf-8 -*-

from twisted.internet import defer, protocol
from twisted.protocols import amp
from twisted.python import log

from sequoia.models import User, MediaEncryptionKey


class RegistrationError(Exception):
    pass


class RegisterUser(amp.Command):
    arguments = [
        ('mport', amp.Integer()),
    ]
    response = [
        ('mport', amp.Integer()),
        ('keys_pair', amp.Integer()),
        ('self_nick', amp.Unicode()),
        ('participants', amp.ListOf(amp.Unicode())),
    ]
    errors = {
        RegistrationError: 'reg_err',
    }


class ServerProtocol(amp.AMP):

    mport = None
    user = None

    @RegisterUser.responder
    def register(self, mport):
        self.mport = mport
        return self.factory.register_client(self).addCallback(
            self._on_register)

    def _on_register(self, (user, participants)):
        self.user = user
        return {
            'mport': self.factory.get_media_port(),
            'self_nick': self.user.nick_name,
            'keys_pair': self.user.sequence_number,
            'participants': participants,
        }

    def get_serial_number(self):
        return str(self.transport.getPeerCertificate().get_serial_number())

    def connectionLost(self, reason):
        self.factory.unregister_client(self)


class ServerClientsFactory(protocol.Factory):

    protocol = ServerProtocol

    def __init__(self):
        self.media_tx = MediaProtocol()
        self.clients = {}

    def get_media_port(self):
        return self.media_tx.transport.getHost().port

    @defer.inlineCallbacks
    def register_client(self, client):
        users = yield User.find(where=['login = ?', client.get_serial_number()])
        if not users:
            raise RegistrationError("Unknown user")
        user, = users
        if user.nick_name in self.clients:
            raise RegistrationError("Already connected")
        keys_pair_count = yield MediaEncryptionKey.count(where=[
            'user_id = ?', user.id])
        if not keys_pair_count:
            raise RegistrationError("No media encryption keys")

        # Rotate keys pair
        user.sequence_number = user.sequence_number + 1 \
            if user.sequence_number < keys_pair_count else 1
        yield user.save()

        participants = self.clients.keys()
        self.clients[user.nick_name] = client
        # TODO: send info to participants
        # TODO: start media pipe
        defer.returnValue((user, participants))

    def unregister_client(self, client):
        del self.clients[client.user.nick_name]
        participants = self.clients.keys()
        # TODO: send info to participants
        # TODO: stop media pipe


class ClientProtocol(amp.AMP):
    pass


class ClientFactory(protocol.ClientFactory):

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


class MediaProtocol(protocol.DatagramProtocol):

    def __init__(self, address=None):
        # add codec and ciphers
        self.address = address
        self.on_start = defer.Deferred()
        self.buffer_in = ""
        self.buffer_out = ""

    def startProtocol(self):
        if self.on_start is not None:
            d, self.on_start = self.on_start, None
            d.callback(None)

    def datagramReceived(self, data, address):
        if self.address is not None and address != self.address:
            log.msg("Message from unknown peer: {0}:{1}.".format(*address))
            return
        log.msg("Incoming {0} bytes from {1}:{2}.".format(len(data), *address))
