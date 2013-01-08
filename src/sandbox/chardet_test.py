# -*- coding: utf-8 -*-
import sys
import chardet
import codecs

print("system encoding: %s" % (sys.getfilesystemencoding()))
first_arg = sys.argv[1]
#first_arg="réception"
#first_arg="て感じでしょうか研"
print first_arg
print("chardet = %s\n" % chardet.detect(first_arg))
res_char = chardet.detect(first_arg)
print type(first_arg)
 

 
first_arg_unicode = first_arg.decode(res_char['encoding'])
print first_arg_unicode
print type(first_arg_unicode)
 
utf8_arg = first_arg_unicode.encode("utf-8")
print type(utf8_arg)
print utf8_arg