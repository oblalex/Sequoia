#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pyaudio
import optparse
import simplejson as json
import speex
import sys

from OpenSSL.SSL import Error as SSLError
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet import defer, reactor
from twisted.python import log

from sequoia.constants import AUDIO
from sequoia.protocol import ClientFactory, ClientMediaProtocol, RegisterUser
from sequoia.security import ClientCtxFactory


def parse_args():
    usage = """usage: %prog [--host=HOST] --port=PORT --key=KEY --crt=CRT --media_keys=MEDIA_KEYS"""
    parser = optparse.OptionParser(usage)

    help = "Server's host. Default: localhost"
    parser.add_option('--host', default='localhost', help=help)

    help = "Server's port."
    parser.add_option('--port', type='int', help=help)

    help = "Path to private key. Default: client.key"
    parser.add_option('--key', default='client.key', help=help)

    help = "Path to certificate. Default: client.crt"
    parser.add_option('--crt', default='client.crt', help=help)

    help = "Path to media keys. Default: media.keys"
    parser.add_option('--media_keys', default='media.keys', help=help)

    options, args = parser.parse_args()
    if not options.port:
        parser.error("Server's port is not specified.")
    if not options.key:
        parser.error("Path to private key is not specified.")
    if not options.crt:
        parser.error("Path to private certificate is not specified.")
    if not options.media_keys:
        parser.error("Path to media keys is not specified.")

    return (options.host, options.port, options.key, options.crt,
        options.media_keys, )


def main():
    host, port, key, crt, media_keys = parse_args()

    def endpoint_done(protocol):
        d = media_tx.on_start
        m_listener = reactor.listenUDP(0, media_tx, interface=host)
        mport = m_listener.getHost().port
        factory.host = protocol.transport.getHost().host
        return d.addCallback(lambda _: protocol.register(mport=mport))

    def endpoint_failed(err):
        err.trap(SSLError)
        return defer.fail(Exception("Invalid SSL credentials."))

    def connection_done(result):
        mport = result.pop('mport')
        keys_pair_num = str(result.pop('keys_pair'))
        keys = all_keys[keys_pair_num]
        keys.reverse()
        media_tx.configure(speexxx, keys, (factory.host, mport))
        reactor.callLater(0, stream.start_stream)

        print result.get('self_nick')
        print result.get('participants')

    def connection_failed(reason):
        print "FAIL: %s" % reason.value
        reactor.stop()

    def audio_callback(in_data, frame_count, time_info, status):
        out_data = media_tx.push_n_pull(in_data)
        return (out_data, pyaudio.paContinue)

    with open(media_keys, 'r') as f:
        all_keys = json.loads(f.read())

    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=audio.get_format_from_width(AUDIO['width']),
        channels=AUDIO['channels'], rate=AUDIO['rate'],
        input=True, output=True, stream_callback=audio_callback)

    speexxx = speex.new()
    media_tx = ClientMediaProtocol()
    factory = ClientFactory(media_tx)
    ctx_factory = ClientCtxFactory(key, crt)
    endpoint = SSL4ClientEndpoint(reactor, host, port, ctx_factory)
    endpoint.connect(factory).addCallbacks(
        endpoint_done, endpoint_failed).addCallbacks(
        connection_done, connection_failed)
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
