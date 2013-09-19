#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import gtk2reactor
gtk2reactor.install()

from hello_glade import HelloWorldGlade


def main():
    hello = HelloWorldGlade()

    from twisted.internet import reactor
    reactor.run()


if __name__ == "__main__":
    main()
