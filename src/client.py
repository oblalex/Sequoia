#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk
pygtk.require('2.0')

from twisted.internet import gtk2reactor
gtk2reactor.install()

import gtk
import pyaudio
import optparse
import os
import simplejson as json
import shelve
import speex
import sys

from OpenSSL.SSL import Error as SSLError
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet import defer, reactor
from twisted.python import log

from sequoia.constants import AUDIO
from sequoia.protocol import ClientFactory, ClientMediaProtocol, RegisterUser
from sequoia.security import ClientCtxFactory


def get_ui_dir():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "sequoia/ui")


class KeysSelectingWindow(object):

    def __init__(self, paths):
        self.paths = paths

        gladefile = os.path.join(get_ui_dir(), "keys.glade")
        root = gtk.Builder()
        root.add_from_file(gladefile)

        self.selectors = {
            'pkey': root.get_object('pkey_selector'),
            'crt': root.get_object('crt_selector'),
            'mkeys': root.get_object('mkeys_selector'),
        }
        self._load_paths(self.paths, self.selectors)
        self.wnd = root.get_object('keys_wnd')

        signals = {
            'on_apply_btn_clicked': self.on_apply_btn_clicked,
            'on_close_btn_clicked': self.on_close_btn_clicked,
        }
        root.connect_signals(signals)

    def _load_paths(self, paths, selectors):
        p = paths.get('private_key')
        if p:
            selectors['pkey'].set_filename(p)
        p = paths.get('certificate')
        if p:
            selectors['crt'].set_filename(p)
        p = paths.get('media_keys')
        if p:
            selectors['mkeys'].set_filename(p)

    def _save_paths(self, paths, selectors):
        paths.update({
            'private_key': selectors['pkey'].get_filename(),
            'certificate': selectors['crt'].get_filename(),
            'media_keys': selectors['mkeys'].get_filename(),
        })

    def on_apply_btn_clicked(self, widget):
        self._save_paths(self.paths, self.selectors)
        self.wnd.destroy()

    def on_close_btn_clicked(self, widget):
        self.wnd.destroy()

    def show(self):
        self.wnd.show()


class MainWindow(object):

    def __init__(self):
        self.settings = self._init_settings()
        gladefile = os.path.join(get_ui_dir(), "main.glade")
        root = gtk.Builder()
        root.add_from_file(gladefile)

        self.participants_store = self._init_participants_tree(root)
        self.buttons = {
            'connection': root.get_object('connetcion_btn'),
            'cipher': root.get_object('cipher_btn'),
            'recording': root.get_object('recording_btn'),
        }

        signals = {
            'on_keys_bnt_clicked': self.on_keys_bnt_clicked,
            'on_conferences_btn_clicked' : self.on_conferences_btn_clicked,
            'on_recording_btn_toggled': self.on_recording_btn_toggled,
            'on_cipher_btn_toggled': self.on_cipher_btn_toggled,
            'on_connetcion_btn_toggled': self.on_connetcion_btn_toggled,
            'on_main_wnd_delete_event': self.delete_event,
        }
        root.connect_signals(signals)

        self.wnd = root.get_object('main_wnd')
        self.wnd.show()

    def _init_settings(self):
        settings = gtk.settings_get_default()
        settings.props.gtk_button_images = True

        dirname = os.path.join(os.path.expanduser("~"), ".config", "sequoia")
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        pathname = os.path.join(dirname, "settings")
        settings = shelve.open(pathname, writeback=True)
        return settings

    def _init_participants_tree(self, root):
        store = gtk.ListStore(str, )

        model = gtk.TreeModelSort(store)
        model.set_sort_column_id(0, gtk.SORT_ASCENDING)

        column = gtk.TreeViewColumn(
            "Participants",
            gtk.CellRendererText(),
            text=0)
        column.set_sort_column_id(0)

        tree = root.get_object('participants_tree')
        tree.set_model(model)
        tree.append_column(column)

        return store

    # for row in self.participants_store:
    #     if row[0] == 'baz':
    #         self.participants_store.remove(row.iter)
    #         break
    # self.participants_store.append(['baz', ])

    def on_conferences_btn_clicked(self, widget):
        pass

    def on_keys_bnt_clicked(self, widget):
        key_paths = self.settings.setdefault('keys', {})
        KeysSelectingWindow(key_paths).show()

    def on_cipher_btn_toggled(self, widget):
        filename = 'lock.png' if widget.get_active() else \
                   'lock-open.png'
        img = self.buttons['cipher'].get_image()
        img.set_from_file(os.path.join(get_ui_dir(), filename))

    def on_recording_btn_toggled(self, widget):
        filename = 'microphone.png' if widget.get_active() else \
                   'microphone-muted.png'
        img = self.buttons['recording'].get_image()
        img.set_from_file(os.path.join(get_ui_dir(), filename))

    def on_connetcion_btn_toggled(self, widget):
        # if failed: widget.set_active(False)
        label = gtk.STOCK_DISCONNECT if widget.get_active() else \
                gtk.STOCK_CONNECT
        self.buttons['connection'].set_label(label)

    def delete_event(self, widget, event):
        self.settings.close()
        gtk.main_quit()
        reactor.stop()
        return False


def main():
    # host, port, key, crt, media_keys = parse_args()

    # def endpoint_done(protocol):
    #     d = media_tx.on_start
    #     m_listener = reactor.listenUDP(0, media_tx)
    #     mport = m_listener.getHost().port
    #     factory.host = protocol.transport.getPeer().host
    #     return d.addCallback(lambda _: protocol.register(mport=mport))

    # def endpoint_failed(err):
    #     err.trap(SSLError)
    #     return defer.fail(Exception("Invalid SSL credentials."))

    # def connection_done(result):
    #     mport = result.pop('mport')
    #     keys_pair_num = str(result.pop('keys_pair'))
    #     keys = all_keys[keys_pair_num]
    #     keys.reverse()
    #     media_tx.configure(speexxx, keys, (factory.host, mport))
    #     reactor.callLater(0, stream.start_stream)

    #     print result.get('self_nick')
    #     print result.get('participants')

    # def connection_failed(reason):
    #     print "FAIL: %s" % reason.value
    #     reactor.stop()

    # def audio_callback(in_data, frame_count, time_info, status):
    #     out_data = media_tx.push_n_pull(in_data)
    #     return (out_data, pyaudio.paContinue)

    # with open(media_keys, 'r') as f:
    #     all_keys = json.loads(f.read())

    # audio = pyaudio.PyAudio()
    # stream = audio.open(
    #     format=pyaudio.paInt16,
    #     channels=AUDIO['channels'], rate=AUDIO['rate'],
    #     input=True, output=True, stream_callback=audio_callback)

    # speexxx = None#speex.new()
    # media_tx = ClientMediaProtocol()
    # factory = ClientFactory(media_tx)
    # ctx_factory = ClientCtxFactory(key, crt)
    # endpoint = SSL4ClientEndpoint(reactor, host, port, ctx_factory)
    # endpoint.connect(factory).addCallbacks(
    #     endpoint_done, endpoint_failed).addCallbacks(
    #     connection_done, connection_failed)
    wnd = MainWindow()
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    main()
