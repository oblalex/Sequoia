# -*- coding: utf-8 -*-

from OpenSSL import SSL
from twisted.internet import ssl
from twisted.python import log

from pprint import pprint


class ServerContextFactory(ssl.DefaultOpenSSLContextFactory):

    def __init__(self, privateKeyFileName, certificateFileName, caPEM_FileName,
                 sslmethod=SSL.SSLv23_METHOD, _contextFactory=SSL.Context):
        self.caPEM_FileName = caPEM_FileName
        ssl.DefaultOpenSSLContextFactory.__init__(self,
            privateKeyFileName, certificateFileName,
            sslmethod, _contextFactory)

    def cacheContext(self):
        ssl.DefaultOpenSSLContextFactory.cacheContext(self)
        self._context.set_verify(
            SSL.VERIFY_PEER | SSL.VERIFY_FAIL_IF_NO_PEER_CERT, self._verify)
        self._context.load_verify_locations(self.caPEM_FileName)

    def _verify(self, connection, x509, errnum, errdepth, ok):
        if not ok:
            log.err(
                "Invalid cert from subject: {0}".format(x509.get_subject()))
            return False
        else:
            return True


class ClientCtxFactory(ssl.ClientContextFactory):

    def __init__(self, privateKeyFileName, certificateFileName):
        self.privateKeyFileName = privateKeyFileName
        self.certificateFileName = certificateFileName

    def getContext(self):
        self.method = SSL.SSLv23_METHOD
        ctx = ssl.ClientContextFactory.getContext(self)
        ctx.use_privatekey_file(self.privateKeyFileName)
        ctx.use_certificate_file(self.certificateFileName)
        return ctx

