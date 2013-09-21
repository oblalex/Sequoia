# -*- coding: utf-8 -*-

import itertools
import pyaudio
import os.path
import struct
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import reactor
from random import randint

from hello_glade import HelloWorldGlade
from sequoia.gost.gost import GOST


def get_key():
    return tuple([randint(0, 32000) for _ in range(8)])

WIDTH = 2
CHANNELS = 1
RATE = 16000

class EchoCipherGlade(HelloWorldGlade):

    def __init__(self, audio):
        super(EchoCipherGlade, self).__init__()
        self.audio = audio
        self.good_key = get_key()
        self.bad_key = get_key()
        self.cipher = GOST(self.good_key)
        self.wrong_decoding = False

    def callback(self, in_data, frame_count, time_info, status):
        dlen = frame_count*WIDTH
        din = [struct.unpack(">LL", in_data[i:i+8]) for i in xrange(0, dlen, 8)]
        enc_out = [self.cipher.encrypt(x) for x in din]

        if self.wrong_decoding:
            self.cipher.set_key(self.bad_key)
            dec_out = [self.cipher.decrypt(x) for x in enc_out]
            self.cipher.set_key(self.good_key)
        else:
            dec_out = [self.cipher.decrypt(x) for x in enc_out]

        out = struct.pack(">"+'L'*(dlen/4), *list(itertools.chain(*dec_out)))
        return (out, pyaudio.paContinue)

    def on_togglebutton_toggled(self, widget, data=None):
        if widget.get_active():
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(WIDTH),
                channels=CHANNELS, rate=RATE,
                input=True, output=True, stream_callback=self.callback)
            reactor.callLater(0, self.stream.start_stream)
        else:
            reactor.callLater(0, self.stream.close)

    def on_checkbox_toggled(self, widget, data=None):
        self.wrong_decoding = widget.get_active()

    def delete_event(self, widget, event, data=None):
        self.audio.terminate()
        return super(EchoCipherGlade, self).delete_event(widget, event, data)
        reactor.stop()


def main():
    audio = pyaudio.PyAudio()
    wnd = EchoCipherGlade(audio)
    reactor.run()


if __name__ == "__main__":
    main()
