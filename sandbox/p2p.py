# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')

import gtk
import itertools
import pyaudio
import re
import os.path
import speex
import struct
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import defer, reactor
from twisted.internet.protocol import DatagramProtocol

from sequoia.gost.gost import GOST


WIDTH = 2
CHANNELS = 1
RATE = 16000
RX_ADDR = r"(?P<ip>\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}):(?P<port>\d+)"


class Cipher(GOST):

    def set_key(self, key):
        super(Cipher, self).set_key(self._str_to_key(key))

    def _str_to_key(self, value):
        assert len(value) == 32
        return struct.unpack('>'+'L'*8, value)


class AudioProtocol(DatagramProtocol):

    def __init__(self, receiver, remote_address):
        self.receiver = receiver
        self.remote_address = remote_address
        self.on_start = defer.Deferred()

    def startProtocol(self):
        if self.on_start is not None:
            d, self.on_start = self.on_start, None
            d.callback(None)

    def send_data(self, data):
        self.transport.write(data, self.remote_address)

    def datagramReceived(self, data, remote_address):
        if remote_address != self.remote_address:
            return
        self.receiver.on_data_received(data)


class MainWindow(object):

    connector = None
    msg_dialog = None

    def __init__(self, audio):
        self.audio = audio
        self.spx = speex.new()
        self.buf = ''

        gladefile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glade/p2p.glade")
        self.wTree = gtk.Builder()
        self.wTree.add_from_file(gladefile)

        key = self.wTree.get_object('local_key').get_text()
        self.cipher = Cipher(key)
        key = self.wTree.get_object('remote_key').get_text()
        self.decipher = Cipher(key)

        self.w_local_address = self.wTree.get_object('local_address')
        self.w_remote_address = self.wTree.get_object('remote_address')

        dic = {
            'on_run_conversation_toggled' : self.on_run_conversation_toggled,
            'on_local_key_focus_out_event': self.on_local_key_focus_out_event,
            'on_remote_key_focus_out_event': self.on_remote_key_focus_out_event,
            'on_wnd_delete_event': self.delete_event,
        }
        self.wTree.connect_signals(dic)
        self.wTree.get_object('wnd').show()

    def on_run_conversation_toggled(self, widget):
        is_active = widget.get_active()
        if is_active:
            local_address = self._validate_address(
                self.w_local_address.get_text())
            remote_address = self._validate_address(
                self.w_remote_address.get_text())
            if not local_address or not remote_address:
                self._show_error_message("Check addresses.")
                widget.set_active(False)
                return
            self.run_conversation(local_address, remote_address)
        else:
            self.stop_conversation()
        self.w_local_address.set_sensitive(not is_active)
        self.w_remote_address.set_sensitive(not is_active)

    def run_conversation(self, (address, port), remote_address):

        def on_network_start(_):
            self.stream = self.audio.open(
                format=self.audio.get_format_from_width(WIDTH),
                channels=CHANNELS, rate=RATE,
                input=True, output=True, stream_callback=self.callback)
            reactor.callLater(0, self.stream.start_stream)

        self.protocol = AudioProtocol(self, remote_address)
        self.protocol.on_start.addCallback(on_network_start)
        self.connector = reactor.listenUDP(
            port, self.protocol, interface=address)

    def stop_conversation(self):
        stream, self.stream = self.stream, None
        reactor.callLater(0, stream.close)
        connector, self.connector = self.connector, None
        self.protocol = None
        connector.stopListening()

    def callback(self, in_data, frame_count, time_info, status):
        # Encode with speex
        dlen = frame_count*WIDTH
        din = list(struct.unpack('h'*(dlen/2), in_data))
        spx_out = self.spx.encode(din)

        # Cipher with GOST
        enc_len = len(spx_out)
        enc_in = [struct.unpack('>LL', spx_out[i:i+8])
            for i in xrange(0, enc_len, 8)]
        enc_out = [self.cipher.encrypt(x) for x in enc_in]
        out = struct.pack(
            '>'+'L'*(enc_len/4), *list(itertools.chain(*enc_out)))

        # Send to peer
        self.protocol.send_data(out)

        # Get received data or silence
        idx = min(len(self.buf), dlen)
        if idx:
            out, self.buf = self.buf[:idx], self.buf[idx:]
        else:
            out = ''
        delta = dlen-idx
        if delta:
            out += '\x00'*delta

        return (out, pyaudio.paContinue)

    def on_data_received(self, in_data):
        # Decipher with GOST
        dlen = len(in_data)
        din = [struct.unpack('>LL', in_data[i:i+8])
            for i in xrange(0, dlen, 8)]
        dec_out = [self.decipher.decrypt(x) for x in din]
        dec = struct.pack('>'+'L'*(dlen/4), *list(itertools.chain(*dec_out)))

        # Decode with speex
        spx_out = self.spx.decode(dec)
        if spx_out:
            out = struct.pack('h'*len(spx_out), *spx_out)

            # Put to buffer
            self.buf += out

    def on_local_key_focus_out_event(self, widget, event):
        def check_value():
            key = self._validate_key(widget.get_text())
            if key:
                self.cipher.set_key(key)
        return self._check_value_on_focus_lost(check_value)

    def on_remote_key_focus_out_event(self, widget, event):
        def check_value():
            key = self._validate_key(widget.get_text())
            if key:
                self.decipher.set_key(key)
        return self._check_value_on_focus_lost(check_value)

    def _check_value_on_focus_lost(self, checker):
        if not self.msg_dialog:
            # Call check later, so event will rich the widget immediately and
            # timeout will not occur
            reactor.callLater(0, checker)
        return False

    def _validate_address(self, value):
        m = re.match(RX_ADDR, value)
        if m:
            d = m.groupdict()
            return (d['ip'], int(d['port']))
        else:
            self._show_error_message("Address is malformed.")
            return None

    def _validate_key(self, value):
        if len(value) == 32:
            return value
        else:
            self._show_error_message("Key must have 32-symbols lenght.")
            return None

    def _show_error_message(self, msg):
        self.msg_dialog = gtk.MessageDialog(self.wnd,
            gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR,
            gtk.BUTTONS_CLOSE, msg)
        self.msg_dialog.run()
        self.msg_dialog.destroy()
        self.msg_dialog = None

    def delete_event(self, widget, event):
        if self.connector:
            self.stop_conversation()
        self.audio.terminate()
        gtk.main_quit()
        reactor.stop()
        return False


def main():
    audio = pyaudio.PyAudio()
    wnd = MainWindow(audio)
    reactor.run()


if __name__ == "__main__":
    main()
