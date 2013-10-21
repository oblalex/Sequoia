# -*- coding: utf-8 -*-

import ctypes
import itertools
import os
import struct
import sys

from twisted.internet.task import LoopingCall

from sequoia.gost.gost import GOST


libmedia_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libmedia.so")
libmedia = ctypes.CDLL(libmedia_path)


class MediaChannel(object):

    def __init__(self, codec, (key_in, key_out)):
        self.codec = codec
        self.cipher = GOST(key_out)
        self.decipher = GOST(key_in)
        self.buffer_in = ''
        self.buffer_out = ''

    def put_in(self, data):
        """Unpack and put data from client to buffer_in."""
        unpacked = self.unpack(data)
        if unpacked is not None:
            self.buffer_in += unpacked
            return len(unpacked)
        else:
            return 0

    def put_out(self, data):
        """Put data from mixer to buffer_out."""
        self.buffer_out += data

    def get_in(self, length):
        """Get unpacked data from server or silence."""
        # return unpacked from buffer_in or silence
        idx = min(len(self.buffer_in), length)
        if idx:
            out, self.buffer_in = self.buffer_in[:idx], self.buffer_in[idx:]
        else:
            out = ''
        delta = length - idx
        if delta:
            out += '\x00' * delta
        return out

    def get_out(self, length):
        """Get packed data from mixer or silence."""
        idx = min(len(self.buffer_out), length)
        if idx:
            out, self.buffer_out = self.buffer_out[:idx], self.buffer_out[idx:]
        else:
            out = ''
        delta = length - idx
        if delta:
            out += '\x00' * delta
        return self.pack(out)

    def pack(self, data):
        # Encode with codec
        dlen = len(data)
        din = list(struct.unpack("%dh" % (dlen/2), data))
        codec_out = self.codec.encode(din)

        # Cipher with GOST
        enc_len = len(codec_out)
        enc_in = [struct.unpack('>LL', codec_out[i:i+8])
            for i in xrange(0, enc_len, 8)]
        enc_out = [self.cipher.encrypt(x) for x in enc_in]
        out = struct.pack(
            '>%dL' % (enc_len/4), *list(itertools.chain(*enc_out)))
        return out

    def unpack(self, data):
        # Decipher with GOST
        dlen = len(data)
        din = [struct.unpack('>LL', data[i:i+8])
            for i in xrange(0, dlen, 8)]
        dec_out = [self.decipher.decrypt(x) for x in din]
        dec = struct.pack('>%dL' % (dlen/4), *list(itertools.chain(*dec_out)))

        # Decode with codec
        codec_out = self.codec.decode(dec)
        return struct.pack("%dh" % len(codec_out), *codec_out) \
            if codec_out else None


class AudioMixer(object):

    def __init__(self, period=0.05):
        self.period = period
        self.channels = []
        self.lcall = LoopingCall(self._mix_channels)

    def start(self):
        self.lcall.start(self.period)

    def stop(self):
        self.lcall.stop()

    def _mix_channels(self):
        min_len = self._min_incoming_data_len()
        if not min_len:
            return
        for channel in self.channels:
            prepared_data, channel.buffer_in = \
                channel.buffer_in[:min_len], channel.buffer_in[min_len:]
            channel.c_in = prepared_data if prepared_data else None

        c_min_len = ctypes.c_int(min_len)
        for channel_a in self.channels:
            out_a = '\x00' * min_len
            c_out_a = ctypes.c_char_p(out_a)
            for channel_b in self.channels:
                if channel_a == channel_b:
                    continue
                c_in_b = channel_b.c_in
                if c_in_b is None:
                    continue
                libmedia.mix_channels(c_out_a, c_in_b, c_min_len)
            channel_a.put_out(out_a)

    def _min_incoming_data_len(self):
        result = sys.maxint
        found = False
        for channel in self.channels:
            in_len = len(channel.buffer_in)
            if in_len:
                result = min(in_len, result)
                found = True
        return result if found else 0

    def register_channel(self, channel):
        assert channel not in self.channels
        self.channels.append(channel)

    def unregister_channel(self, channel):
        assert channel in self.channels
        self.channels.remove(channel)
