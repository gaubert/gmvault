import sys
import chardet
import codecs
 
first_arg = sys.argv[1]
print first_arg
print("chardet = %s\n" % chardet.detect(first_arg))
res_char = chardet.detect(first_arg)
print type(first_arg)
 
print("%s" % (sys.getfilesystemencoding()))
 
first_arg_unicode = first_arg.decode(res_char['encoding'])
print first_arg_unicode
print type(first_arg_unicode)
 
f = codecs.open(first_arg_unicode, 'r', 'utf-8')
unicode_text = f.read()
print type(unicode_text)
print unicode_text.encode(sys.getfilesystemencoding())
