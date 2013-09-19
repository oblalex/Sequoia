# -*- coding: utf-8 -*-

from twisted.trial.unittest import TestCase

from sequoia.gost import GOST


class GOSTTestCase(TestCase):

    def setUp(self):
        self.text = 0xfedcba0987654321
        self.key = 0x1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff
        self.cipher = GOST()
        self.cipher.set_key(self.key)

    def test_right_keys(self):
        encrypted = self.cipher.encrypt(self.text)
        self.assertNotEqual(self.text, encrypted)

        decrypted = self.cipher.decrypt(encrypted)
        self.assertEqual(self.text, decrypted)

    def test_wrong_keys(self):
        encrypted = self.cipher.encrypt(self.text)
        self.assertNotEqual(self.text, encrypted)

        new_key = 0xffff1111222233334444555566667777888899990000aaaabbbbccccddddeeee
        self.cipher.set_key(new_key)

        decrypted = self.cipher.decrypt(encrypted)
        self.assertNotEqual(self.text, decrypted)

        self.cipher.set_key(self.key)

        decrypted = self.cipher.decrypt(encrypted)
        self.assertEqual(self.text, decrypted)
