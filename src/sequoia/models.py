# -*- coding: utf-8 -*-

from twistar.dbobject import DBObject
from twistar.registry import Registry


class User(DBObject):
    HASMANY = [
        'media_encryption_keys',
    ]


class MediaEncryptionKey(DBObject):
    BELONGSTO = [
        'user',
    ]


Registry.register(User, MediaEncryptionKey)
