#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os.path
import sys

import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade


class HelloWorldGlade(object):
    """This is an Hello World GTK application"""

    def __init__(self):
        gladefile = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glade/hello_glade.glade")
        self.wTree = gtk.Builder()
        self.wTree.add_from_file(gladefile)

        self.window = self.wTree.get_object('main_window')
        if (self.window):
            dic = {
                'on_togglebutton_toggled' : self.on_togglebutton_toggled,
                'on_main_window_delete_event': self.delete_event,
                'on_checkbox_toggled': self.on_checkbox_toggled,
            }
            self.wTree.connect_signals(dic)
            self.window.show()

    def on_togglebutton_toggled(self, widget, data=None):
        print "Toggle button is", widget.get_active()

    def on_checkbox_toggled(self, widget, data=None):
        print "Checkbox is", widget.get_active()

    def delete_event(self, widget, event, data=None):
        gtk.main_quit()
        return False


if __name__ == "__main__":
    wnd = HelloWorldGlade()
    gtk.main()
