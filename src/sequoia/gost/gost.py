# -*- coding: utf-8 -*-

import os

from ctypes import CDLL, c_ulong

libgost_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libgost.so")
libgost = CDLL(libgost_path)
libgost.kboxinit()


class GOST(object):

    __GostData = c_ulong * 2
    __GostKey = c_ulong * 8

    def __init__(self, key):
        self.set_key(key)

    def set_key(self, key):
        assert isinstance(key, tuple)
        assert len(key) == 8
        self.key = self.__GostKey(*key)

    def encrypt(self, data):
        dout = self.__GostData(0, 0)
        libgost.gostcrypt(self.__GostData(*data), dout, self.key)
        return tuple(dout)

    def decrypt(self, data):
        dout = self.__GostData(0, 0)
        libgost.gostdecrypt(self.__GostData(*data), dout, self.key)
        return tuple(dout)
