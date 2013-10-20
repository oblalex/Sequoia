# -*- coding: utf-8 -*-

from twisted.internet import defer, protocol
from twisted.protocols import amp
from twisted.python import log

from sequoia.media.media import MediaChannel
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


class UserJoined(amp.Command):
    arguments = [
        ('nick', amp.Unicode()),
    ]
    response = [
        ('ack', amp.Boolean()),
    ]


class UserLeft(amp.Command):
    arguments = [
        ('nick', amp.Unicode()),
    ]
    response = [
        ('ack', amp.Boolean()),
    ]


class ServerProtocol(amp.AMP):

    media_address = None
    user = None

    @RegisterUser.responder
    def register(self, mport):
        self.media_address = (self.transport.getHost().host, mport)
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

    @property
    def serial_number(self):
        return str(self.transport.getPeerCertificate().get_serial_number())

    def connectionLost(self, reason):
        self.factory.unregister_client(self)


class ServerClientsFactory(protocol.Factory):

    protocol = ServerProtocol

    def __init__(self, media_tx):
        self.media_tx = media_tx
        self.clients = {}

    def get_media_port(self):
        return self.media_tx.transport.getHost().port

    @defer.inlineCallbacks
    def register_client(self, client):
        user = yield User.find(
            where=['login = ?', client.serial_number],
            limit=1)
        if not user:
            raise RegistrationError("Unknown user")
        if user.nick_name in self.clients:
            raise RegistrationError("Already connected")
        keys_pair_count = yield MediaEncryptionKey.count(where=[
            'user_id = ?', user.id])
        if not keys_pair_count:
            raise RegistrationError("No media encryption keys")

        # Rotate keys pair
        user.sequence_number = user.sequence_number + 1 \
            if user.sequence_number < keys_pair_count else 1
        keys = yield MediaEncryptionKey.find(
            where=[
                'user_id = ? AND sequence_number = ?',
                user.id, user.sequence_number],
            limit=1)
        if not keys:
            raise RegistrationError("Getting media encryption keys error")
        yield user.save()

        media_keys = (str(keys.k1), str(keys.k2))
        participants = self.clients.keys()

        # Send info to participants
        for c in self.clients.values():
            c.callRemote(UserJoined, nick=user.nick_name)

        self.clients[user.nick_name] = client
        self.media_tx.register_channel(client.media_address, media_keys)
        defer.returnValue((user, participants))

    def unregister_client(self, client):
        if client.user is None:
            return

        self.clients.pop(client.user.nick_name)
        participants = self.clients.keys()

        # Send info to participants
        for c in self.clients.values():
            c.callRemote(UserLeft, nick=client.user.nick_name)

        self.media_tx.unregister_channel(client.media_address)


class ClientProtocol(amp.AMP):

    @UserJoined.responder
    def joined(self, nick):
        print nick, "has joined"
        return {'ack': True}

    @UserLeft.responder
    def left(self, nick):
        print nick, "has left"
        return {'ack': True}

    def register(self, mport):
        return self.callRemote(RegisterUser, mport=mport)


class ClientFactory(protocol.ClientFactory):

    protocol = ClientProtocol
    host = None

    def __init__(self, media_tx):
        self.media_tx = media_tx

    def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye!"
        from twisted.internet import reactor
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print "Connection lost - goodbye!"
        from twisted.internet import reactor
        reactor.stop()


class MediaProtocol(protocol.DatagramProtocol):

    def __init__(self):
        self.on_start = defer.Deferred()

    def startProtocol(self):
        if self.on_start is not None:
            d, self.on_start = self.on_start, None
            d.callback(None)


class ServerMediaProtocol(MediaProtocol):

    def __init__(self, codec, mixer):
        MediaProtocol.__init__(self)
        self.codec = codec
        self.mixer = mixer
        self.channels = {}

    def register_channel(self, address, keys):
        assert address not in self.channels.keys()
        channel = MediaChannel(self.codec, keys)
        self.mixer.register_channel(channel)
        self.channels[address] = channel

    def unregister_channel(self, address):
        assert address in self.channels.keys()
        channel = self.channels.pop(address)
        self.mixer.unregister_channel(channel)

    def datagramReceived(self, data, address):
        channel = self.channels.get(address)
        if not channel:
            log.msg("Got {0} bytes from unknown peer {1}:{2}".format(
                len(data), *address))
            return
        length = channel.put_in(data)
        out_data = channel.get_out(length)
        if self.transport:
            self.transport.write(out_data, address)


class ClientMediaProtocol(MediaProtocol):

    channel = None
    address = None

    def __init__(self):
        MediaProtocol.__init__(self)

    def configure(self, codec, keys, address):
        self.channel = MediaChannel(codec, keys)
        self.address = address

    def datagramReceived(self, data, address):
        if self.address is not None and address != self.address:
            log.msg("Incoming {0} bytes from unknown peer: {1}:{2}.".format(
                len(data), *address))
            return
        self.channel.put_in(data)

    def push_n_pull(self, in_data):
        if self.channel:
            to_send = self.channel.pack(in_data)
            if self.transport:
                self.transport.write(to_send, self.address)
            return self.channel.get_in(len(in_data))
        else:
            return '\x00'*len(in_data)
