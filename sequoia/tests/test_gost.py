# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase
from random import randint

from sequoia.gost.gost import GOST


class GOSTTestCase(TestCase):

    def setUp(self):
        self.text = (100, 200)
        self.key = self._get_key()
        self.cipher = GOST(self.key)

    def _get_key(self):
        return tuple([randint(0, 32000) for _ in range(8)])

    def test_right_keys(self):
        encrypted = self.cipher.encrypt(self.text)
        self.assertNotEqual(self.text, encrypted)

        decrypted = self.cipher.decrypt(encrypted)
        self.assertEqual(self.text, decrypted)

    def test_wrong_keys(self):
        encrypted = self.cipher.encrypt(self.text)
        self.assertNotEqual(self.text, encrypted)

        self.cipher.set_key(self._get_key())

        decrypted = self.cipher.decrypt(encrypted)
        self.assertNotEqual(self.text, decrypted)

        self.cipher.set_key(self.key)

        decrypted = self.cipher.decrypt(encrypted)
        self.assertEqual(self.text, decrypted)
