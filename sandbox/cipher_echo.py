# -*- coding: utf-8 -*-

import itertools
import os
import struct
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pyaudio

from sequoia.gost.gost import GOST


WIDTH = 2
CHANNELS = 1
RATE = 16000


def main():

    key = tuple(range(8))
    cipher = GOST(key)

    def callback(in_data, frame_count, time_info, status):
        dlen = frame_count*WIDTH
        din = [struct.unpack(">LL", in_data[i:i+8]) for i in xrange(0, dlen, 8)]
        enc_out = [cipher.encrypt(x) for x in din]
        dec_out = [cipher.decrypt(x) for x in enc_out]
        out = struct.pack(">"+'L'*(dlen/4), *list(itertools.chain(*dec_out)))
        return (out, pyaudio.paContinue)

    p = pyaudio.PyAudio()
    stream = p.open(format=p.get_format_from_width(WIDTH),
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
                stream_callback=callback)

    from twisted.internet import reactor
    reactor.callWhenRunning(stream.start_stream)
    reactor.run()


if __name__ == "__main__":
    main()
