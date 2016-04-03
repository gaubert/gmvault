import os, base64
from Crypto.Cipher import AES
import hashlib


import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES

class AESEncryptor(object):

    def __init__(self, key): 
        self.bs = 32
        self.key = hashlib.sha256(key.encode()).digest()

    def encrypt(self, raw):
        raw = self._pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:AES.block_size]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self._unpad(cipher.decrypt(enc[AES.block_size:])).decode('utf-8')

    def _pad(self, s):
        return s + (self.bs - len(s) % self.bs) * chr(self.bs - len(s) % self.bs)

    @staticmethod
    def _unpad(s):
        return s[:-ord(s[len(s)-1:])]

if __name__ == '__main__':
    secrets = ['Do or do not there is no try', 'I love Python !!!!']
    key="This is my key"
    enc = AESEncryptor(key)
    for secret in secrets:
        print "Secret:", secret
        encrypted = enc.encrypt(secret) 
        print "Encrypted secret:", encrypted
        print "Clear Secret:" , enc.decrypt(encrypted)
        print '-' *50
