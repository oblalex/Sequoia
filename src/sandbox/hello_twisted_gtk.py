#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet import gtk2reactor
gtk2reactor.install()

from hello_gtk import HelloWorld


def main():
    hello = HelloWorld()

    from twisted.internet import reactor
    reactor.run()


if __name__ == "__main__":
    main()
