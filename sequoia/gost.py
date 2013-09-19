# -*- coding: utf-8 -*-


class GOST(object):

    sbox = (
        (4, 10, 9, 2, 13, 8, 0, 14, 6, 11, 1, 12, 7, 15, 5, 3),
        (14, 11, 4, 12, 6, 13, 15, 10, 2, 3, 8, 1, 0, 7, 5, 9),
        (5, 8, 1, 13, 10, 3, 4, 2, 14, 15, 12, 7, 6, 0, 9, 11),
        (7, 13, 10, 1, 0, 8, 9, 15, 14, 4, 6, 12, 11, 2, 5, 3),
        (6, 12, 7, 1, 5, 15, 13, 8, 4, 10, 9, 14, 0, 3, 11, 2),
        (4, 11, 10, 0, 7, 2, 1, 13, 3, 6, 8, 5, 9, 12, 15, 14),
        (13, 11, 4, 1, 3, 15, 5, 9, 0, 10, 14, 7, 6, 8, 2, 12),
        (1, 15, 13, 0, 5, 7, 10, 4, 9, 2, 3, 14, 6, 11, 8, 12),
    )

    def __init__(self):
        self.master_key = [None] * 8

    def set_key(self, master_key):
        assert GOST._bit_length(master_key) <= 256
        for i in range(8):
            self.master_key[i] = (master_key >> (32 * i)) & 0xFFFFFFFF

    def encrypt(self, plaintext):
        assert GOST._bit_length(plaintext) <= 64
        text_left = plaintext >> 32
        text_right = plaintext & 0xFFFFFFFF
        for i in range(24):
            text_left, text_right = GOST._round_encryption(
                text_left, text_right, self.master_key[i % 8])
        for i in range(8):
            text_left, text_right = GOST._round_encryption(
                text_left, text_right, self.master_key[7 - i])
        return (text_left << 32) | text_right

    def decrypt(self, ciphertext):
        assert GOST._bit_length(ciphertext) <= 64
        text_left = ciphertext >> 32
        text_right = ciphertext & 0xFFFFFFFF
        for i in range(8):
            text_left, text_right = GOST._round_decryption(
                text_left, text_right, self.master_key[i])
        for i in range(24):
            text_left, text_right = GOST._round_decryption(
                text_left, text_right, self.master_key[(7 - i) % 8])
        return (text_left << 32) | text_right

    @staticmethod
    def _bit_length(x):
        assert x >= 0
        return len(bin(x)) - 2

    @classmethod
    def _f_function(cls, input, key):
        assert GOST._bit_length(input) <= 32
        assert GOST._bit_length(key)   <= 32
        temp = input ^ key
        output = 0
        for i in range(8):
            output |= ((cls.sbox[i][(temp >> (4 * i)) & 0b1111]) << (4 * i))
        output = ((output >> 11) | (output << (32 - 11))) & 0xFFFFFFFF
        return output

    @staticmethod
    def _round_encryption(input_left, input_right, round_key):
        output_left = input_right
        output_right = input_left ^ GOST._f_function(input_right, round_key)
        return output_left, output_right

    @staticmethod
    def _round_decryption(input_left, input_right, round_key):
        output_right = input_left
        output_left = input_right ^ GOST._f_function(input_left, round_key)
        return output_left, output_right
