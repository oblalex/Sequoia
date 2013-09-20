# -*- coding: utf-8 -*-

from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import reactor

import sys
import os.path
import pyaudio

sys.path.append('..')

from hello_glade import HelloWorldGlade
from sequoia.gost import GOST


class EchoCipherGlade(HelloWorldGlade):

    WIDTH = 2
    CHANNELS = 1
    RATE = 16000

    def __init__(self, audio):
        self.audio = audio
        super(EchoCipherGlade, self).__init__()
        key = 0x1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff
        self.cipher = GOST()
        self.cipher.set_key(key)

        self.lut_enc = []
        self.lut_dec = {}
        self.lut_dec_wrong = {}
        self.wrong_decoding = False

        for x in xrange(256):
            enc = self.cipher.encrypt(x)
            self.lut_enc.append(enc)
            self.lut_dec[enc] = x
            self.lut_dec_wrong[enc] = (x % 4) * 64

    def callback(self, in_data, frame_count, time_info, status):
        bytes = [ord(x) for x in in_data]
        encrypted = [self.lut_enc[x] for x in bytes]
        lut = self.lut_dec_wrong if self.wrong_decoding else self.lut_dec
        decrypted = [lut[x] for x in encrypted]
        bytes = ''.join([chr(x) for x in decrypted])
        return (bytes, pyaudio.paContinue)

    def on_togglebutton_toggled(self, widget, data=None):
        if widget.get_active():
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(self.WIDTH),
                channels=self.CHANNELS, rate=self.RATE,
                input=True, output=True, stream_callback=self.callback)
            reactor.callLater(0, self.stream.start_stream)
        else:
            reactor.callLater(0, self.stream.close)

    def on_checkbox_toggled(self, widget, data=None):
        self.wrong_decoding = widget.get_active()

    def delete_event(self, widget, event, data=None):
        self.audio.terminate()
        return super(EchoCipherGlade, self).delete_event(widget, event, data)


def main():
    audio = pyaudio.PyAudio()
    wnd = EchoCipherGlade(audio)
    reactor.run()


if __name__ == "__main__":
    main()
