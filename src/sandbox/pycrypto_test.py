import os, base64
from Crypto.Cipher import AES
import hashlib

class Encryptor(object):
    # the block size for the cipher object; must be 16, 24, or 32 for AES
    block_size = 32
    padding = '{'
    def __init__(self, secret):
        self.secret = hashlib.sha256(secret).digest()
        self.clear_secret = secret
        self.cipher = AES.new(self.secret)
        
    def __pad__(self, clear_string):
        return clear_string + (self.block_size - len(clear_string) % self.block_size) * self.padding 
    def encode(self, clear_string):
        return base64.b64encode(self.cipher.encrypt(self.__pad__(clear_string)))
    def decode(self, encoded_string):
        return self.cipher.decrypt(base64.b64decode(encoded_string)).rstrip(self.padding)

if __name__ == '__main__':
    secrets = ['Do or do not there is no try', 'I love Python !!!!']
    for secret in secrets:
        enc = Encryptor(secret)
        cs = "#Almyqspnlg0"
        print "Padding" , enc.__pad__(cs)
        print "Secret" , enc.secret
        print "Clear Secret" , enc.clear_secret
        es = enc.encode(cs)
        print "Encoded: " , es
        ds = enc.decode(es)
        print "Decoded: " , ds
        print '-' *50
