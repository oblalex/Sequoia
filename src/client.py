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


class ConferencesWindow(object):

    def __init__(self, info):
        self.info = info
        gladefile = os.path.join(get_ui_dir(), "conferences.glade")
        root = gtk.Builder()
        root.add_from_file(gladefile)
        self.wnd = root.get_object('confs_wnd')
        self.tree = self._init_conferences_tree(root, self.info)

        signals = {
            'on_add_btn_clicked': self.on_add_btn_clicked,
            'on_delete_btn_clicked': self.on_delete_btn_clicked,
            'on_ok_btn_clicked': self.on_ok_btn_clicked,
        }
        root.connect_signals(signals)

    def _init_conferences_tree(self, root, info):
        store = gtk.ListStore(str, str, int)
        model = gtk.TreeModelSort(store)
        model.set_sort_column_id(0, gtk.SORT_ASCENDING)

        tree = root.get_object('confs_tree')
        tree.set_model(model)
        self._init_columns(tree)

        conferences = info.setdefault('conferences', [])
        for conference in conferences:
            store.append(conference)
        if conferences:
            tree.set_cursor(info.setdefault('current', 0))

        return tree

    def _init_columns(self, tree):
        column = self._create_column("Name", 0)
        tree.append_column(column)

        column = self._create_column("Address", 1)
        tree.append_column(column)

        column = self._create_column("Port", 2, type_func=int, resizable=False)
        tree.append_column(column)

    def _create_column(self, name, id, type_func=str, resizable=True):

        def edited_callback(cell, path, new_value):
            if not new_value:
                self._show_error("Value cannot be empty.")
                return
            try:
                value = type_func(new_value)
            except ValueError:
                msg = "'{0}' is wrong {1} value.".format(
                    new_value, type_func.__name__)
                self._show_error(msg)
            else:
                self._get_row(path)[id] = value

        renderer = gtk.CellRendererText()
        renderer.connect('edited', edited_callback)
        renderer.set_property('editable', True)

        column = gtk.TreeViewColumn(name, renderer, text=id)
        column.set_sort_column_id(id)
        column.set_resizable(resizable)
        return column

    def _get_row_cursor(self, path):
        return self.tree.get_model().convert_path_to_child_path(path)

    def _get_row(self, path):
        return self.store[self._get_row_cursor(path)]

    def _show_error(self, message):
        md = gtk.MessageDialog(
            self.wnd, gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
            message)
        md.run()
        md.destroy()

    @property
    def store(self):
        return self.tree.get_model().get_model()

    @property
    def current_cursor(self):
        cursor = self.tree.get_cursor()[0]
        if cursor is not None:
            (cursor, ) = cursor
        return cursor

    def on_add_btn_clicked(self, widget):

        model = self.tree.get_model()
        if len(model) > 0:
            cursor = self.current_cursor
            selected_name, address, port = model[cursor]

            chunks = selected_name.rsplit('.', 1)
            try:
                suffix = int(chunks[1]) + 1
            except:
                suffix = 1

            while True:
                name = "{0}.{1}".format(chunks[0], suffix)
                try:
                    next_name = model[cursor + 1][0]
                except IndexError:
                    break
                if name != next_name:
                    break
                suffix += 1
                cursor += 1

            data = (name, address, port)
            cursor += 1
        else:
            data = ("Default", "192.168.1.2", 9876)
            cursor = 0

        self.store.append(data)
        self.tree.set_cursor(cursor)

    def on_delete_btn_clicked(self, widget):
        if not len(self.store):
            return
        if self.current_cursor is None:
            return
        (cursor, ) = self._get_row_cursor(self.current_cursor)
        del self.store[cursor]
        if len(self.store) and self.current_cursor is None:
            self.tree.set_cursor(0)

    def on_ok_btn_clicked(self, widget):
        sorted_store = self.tree.get_model()
        self.info['conferences'] = [(r[0], r[1], r[2]) for r in sorted_store]
        self.info['current'] = self.current_cursor
        self.wnd.destroy()

    def show(self):
        self.wnd.show()


class MainWindow(object):

    def __init__(self):
        self.settings = self._init_settings()
        gladefile = os.path.join(get_ui_dir(), "main.glade")
        root = gtk.Builder()
        root.add_from_file(gladefile)

        self.store = self._init_participants_tree(root)
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

    def on_conferences_btn_clicked(self, widget):
        conf_info = self.settings.setdefault('conferences_info', {})
        ConferencesWindow(conf_info).show()

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
    gtk.settings_get_default().props.gtk_button_images = True
    main()
