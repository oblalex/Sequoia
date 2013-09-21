# -*- coding: utf-8 -*-

import pyaudio
import speex
import struct


WIDTH = 2
CHANNELS = 1
RATE = 16000


def main():

    spx = speex.new()
    buf = []

    def callback(in_data, frame_count, time_info, status):
        dlen = frame_count*WIDTH
        din = list(struct.unpack('h'*(dlen/2), in_data))
        encoded = spx.encode(din)
        dout = spx.decode(encoded)

        delta = len(din)-len(dout)
        if delta > 0:
            x = min(delta, len(buf))
            dout += map(buf.pop, [0,]*x)
            dout += [0,]*(delta-x)
        elif delta < 0:
            buf.extend(dout[len(din):len(dout)])
            dout = dout[:len(din)]

        out = struct.pack('h'*len(dout), *dout)
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
