# -*- coding: utf-8 -*-
import sys
import unicodedata

def ascii_hex(str):
   new_str = ""
   for c in str:
      new_str += "%s=hex[%s]," % (c,hex(ord(c)))
   return new_str
                
def convert_to_utf8(a_str):
    """
    """
    if type(a_str) != type(u'a'):
		#import chardet
		#char_enc = chardet.detect(a_str)
		#print("detected encoding = %s" % (char_enc))
		#print("system machine encoding = %s" % (sys.getdefaultencoding()))
		#u_str = unicode(a_str, char_enc['encoding'], errors='ignore')
		u_str = unicode(a_str, 'cp437', errors='ignore')
    else:
        print("Already unicode do not convert")
        u_str = a_str

    print("raw unicode = %s" % (u_str))
    #u_str = unicodedata.normalize('NFKC',u_str)
    u_str = u_str.encode('unicode_escape').decode('unicode_escape')
    print("unicode escape = %s" % (u_str))
    print("normalized unicode(NFKD) = %s" % (repr(unicodedata.normalize('NFKD',u_str))))
    print("normalized unicode(NFKC) = %s" % (repr(unicodedata.normalize('NFKC',u_str))))
    print("normalized unicode(NFC) = %s" % (repr(unicodedata.normalize('NFC',u_str))))
    print("normalized unicode(NFD) = %s" % (repr(unicodedata.normalize('NFD',u_str))))
    hex_s = ascii_hex(u_str)
    print("Hex ascii %s" % (hex_s))
    utf8_arg = u_str
    #utf8_arg = u_str.encode("utf-8")
    
    return utf8_arg

if __name__ == '__main__':

   u_str = u"label:èévader"
   convert_to_utf8(sys.argv[1])
   #convert_to_utf8(u_str)
