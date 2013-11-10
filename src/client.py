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
from twisted.internet import defer, reactor
from twisted.internet.endpoints import SSL4ClientEndpoint
from twisted.internet.error import ConnectionRefusedError
from twisted.python import log

from sequoia.constants import AUDIO
from sequoia.protocol import ClientFactory, ClientMediaProtocol, RegisterUser
from sequoia.security import ClientCtxFactory


def get_ui_dir():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "sequoia/ui")


def show_error(message, wnd=None):
    md = gtk.MessageDialog(
        wnd, gtk.DIALOG_DESTROY_WITH_PARENT,
        gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
        message)
    md.run()
    md.destroy()


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

        column = self._create_column("Host", 1)
        tree.append_column(column)

        column = self._create_column("Port", 2, type_func=int, resizable=False)
        tree.append_column(column)

    def _create_column(self, name, id, type_func=str, resizable=True):

        def edited_callback(cell, path, new_value):
            if not new_value:
                show_error("Value cannot be empty.", self.wnd)
                return
            try:
                value = type_func(new_value)
            except ValueError:
                msg = "'{0}' is wrong {1} value.".format(
                    new_value, type_func.__name__)
                show_error(msg, self.wnd)
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
            selected_name, host, port = model[cursor]

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

            data = (name, host, port)
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

    media_keys = None
    media_tx = None
    client = None
    codec = None
    stream = None
    do_exit = False

    def __init__(self, audio):
        self.audio = audio
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

        value = self.settings.setdefault('record_input', True)
        self.buttons['recording'].set_active(value)
        self.update_recording_btn(value)

        value = self.settings.setdefault('do_cipher', True)
        self.buttons['cipher'].set_active(value)
        self.update_cipher_btn(value)

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
        self.settings['do_cipher'] = widget.get_active()
        self.update_cipher_btn(widget.get_active())

    def update_cipher_btn(self, value):
        filename = 'lock.png' if value else \
                   'lock-open.png'
        img = self.buttons['cipher'].get_image()
        img.set_from_file(os.path.join(get_ui_dir(), filename))

        if self.media_tx and self.media_tx.channel:
            self.media_tx.channel.do_cipher = value

    def on_recording_btn_toggled(self, widget):
        self.settings['record_input'] = widget.get_active()
        self.update_recording_btn(widget.get_active())

    def update_recording_btn(self, value):
        filename = 'microphone.png' if value else 'microphone-muted.png'
        img = self.buttons['recording'].get_image()
        img.set_from_file(os.path.join(get_ui_dir(), filename))

    def on_connetcion_btn_toggled(self, widget):
        if widget.get_active():
            if (not self._validate_files()
                or not self._validate_conference()
                or not self._load_media_keys()):
                widget.set_active(False)
                return
            self.buttons['connection'].set_label("Connecting...")

            self.media_tx = ClientMediaProtocol()
            factory = ClientFactory(self.media_tx)
            factory.on_connection_lost.addBoth(self.connection_lost)

            keys = self.settings['keys']
            ctx_factory = ClientCtxFactory(
                keys['private_key'], keys['certificate'])

            c_id = self.settings['conferences_info']['current']
            c_info = self.settings['conferences_info']['conferences'][c_id]
            name, host, port = c_info

            endpoint = SSL4ClientEndpoint(reactor, host, port, ctx_factory)
            endpoint.connect(factory).addCallbacks(
                self.endpoint_done, self.endpoint_failed).addCallbacks(
                self.connection_done, self.connection_failed)
        elif self.client:
            self.client.transport.loseConnection()

    def _validate_files(self):
        keys = self.settings.get('keys')
        if not keys:
            show_error("Please, check your keys settings", self.wnd)
            return False
        for k in ['private_key', 'certificate', 'media_keys', ]:
            name = k.replace('_', ' ')
            filename = keys.get(k)
            if not filename:
                show_error("Please, select {0} file".format(name), self.wnd)
                return False
            if not os.path.isfile(filename):
                show_error("Invalid {0} file".format(name), self.wnd)
                return False
        return True

    def _validate_conference(self):

        def on_unconfigured():
            show_error("Please, configure conferences")
            return False

        c_info = self.settings.get('conferences_info')
        if not c_info:
            return on_unconfigured()
        confs = c_info.get('conferences')
        if not confs:
            return on_unconfigured()
        current = c_info.get('current')
        if current is None or current < 0 or current > len(confs):
            show_error("Please, select conference")
            return False

        return True

    def _load_media_keys(self):
        try:
            with open(self.settings['keys']['media_keys'], 'r') as f:
                self.media_keys = json.loads(f.read())
        except IOError:
            show_error("Could not read media keys file", self.wnd)
            return False
        except json.JSONDecodeError:
            show_error("Media keys file has invalid format", self.wnd)
            return False
        return True

    def endpoint_done(self, protocol):
        self.client = protocol
        protocol.user_joined_cb = self.on_user_joined
        protocol.user_left_cb = self.on_user_left

        d = self.media_tx.on_start
        m_listener = reactor.listenUDP(0, self.media_tx)
        mport = m_listener.getHost().port
        return d.addCallback(lambda _: protocol.register(mport=mport))

    def endpoint_failed(self, failure):
        failure.trap(SSLError)
        show_error("Invalid SSL credentials", self.wnd)
        self.connection_closed()
        return failure

    def connection_done(self, result):
        if result.get('use_codec') and self.codec is None:
            self.codec = speex.new()

        keys_pair_num = str(result.pop('keys_pair'))
        keys = self.media_keys[keys_pair_num]
        keys.reverse()

        mport = result.pop('mport')
        remote_media_addr = (self.client.transport.getPeer().host, mport)

        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=AUDIO['channels'], rate=AUDIO['rate'],
            input=True, output=True, stream_callback=self.on_audio_ready)
        self.media_tx.configure(self.codec, keys, remote_media_addr)
        self.media_tx.channel.do_cipher = self.settings['do_cipher']

        reactor.callLater(0, self.stream.start_stream)

        self.store.append((result['self_nick'] + " (you)", ))
        for nick_name in result['participants']:
            self.store.append((nick_name, ))

        self.buttons['connection'].set_label(gtk.STOCK_DISCONNECT)

    def connection_failed(self, failure):
        e = failure.trap(ConnectionRefusedError)
        show_error("Connection refused", self.wnd)
        self.connection_lost()

    def connection_lost(self, reason=None):
        self.media_keys = None
        self.media_tx = None
        if self.client is not None:
            self.client.user_joined_cb = None
            self.client.user_left_cb = None
            self.client = None
        if self.stream is not None:
            self.stream.close()
            self.stream = None

        self.store.clear()

        widget = self.buttons['connection']
        widget.set_label(gtk.STOCK_CONNECT)
        widget.set_active(False)

        if self.do_exit:
            self.exit()

    def delete_event(self, widget, event):
        if self.client is None:
            self.exit()
        else:
            self.do_exit = True
            self.client.transport.loseConnection()
        return False

    def exit(self):
        self.settings.close()
        gtk.main_quit()
        reactor.stop()

    def on_user_joined(self, nick_name):
        self.store.append((nick_name, ))

    def on_user_left(self, nick_name):
        for row in self.store:
            if row[0] == nick_name:
                self.store.remove(row.iter)
                break

    def on_audio_ready(self, in_data, frame_count, time_info, status):
        if self.is_audio_input_enabled:
            self.media_tx.push(in_data)
        out_data = self.media_tx.pull(len(in_data))
        return (out_data, pyaudio.paContinue)

    @property
    def is_audio_input_enabled(self):
        return self.settings.get('record_input', True)


def main():
    audio = pyaudio.PyAudio()
    wnd = MainWindow(audio)
    reactor.run()


if __name__ == "__main__":
    log.startLogging(sys.stdout)
    gtk.settings_get_default().props.gtk_button_images = True
    main()
