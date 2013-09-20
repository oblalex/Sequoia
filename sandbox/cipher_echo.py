# -*- coding: utf-8 -*-

import sys
sys.path.append("..")

import pyaudio

from sequoia.gost import GOST


WIDTH = 2
CHANNELS = 1
RATE = 16000


def main():

    key = 0x1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff
    cipher = GOST()
    cipher.set_key(key)

    # Using Look-up tables to increase performance
    lut_enc = []
    lut_dec = {}
    for x in xrange(256):
        enc = cipher.encrypt(x)
        lut_enc.append(enc)
        lut_dec[enc] = x

    def callback(in_data, frame_count, time_info, status):
        bytes = [ord(x) for x in in_data]
        encrypted = [lut_enc[x] for x in bytes]
        decrypted = [lut_dec[x] for x in encrypted]
        bytes = ''.join([chr(x) for x in decrypted])
        return (bytes, pyaudio.paContinue)

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
