import sys
import re

def find_version(path):

    fd = open(path)

    for line in fd:
        index = line.find("GMVAULT_VERSION=\"")
        if index > -1:
            print(line[index+17:-2])
            return line[index+17:-2]

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % (path))

VERSION_PATTERN = r'###GMVAULTVERSION###' 
VERSION_RE      = re.compile(VERSION_PATTERN)

def add_version(a_input, a_output, a_version):
    """
	"""
    the_in  = open(a_input, 'r')
    the_out = open(a_output, 'w')
    for line in the_in:
        line = VERSION_RE.sub(a_version, line)
        the_out.write(line)

if __name__ == '__main__':

  if len(sys.argv) < 4:
     print("Error: need more parameters for %s." % (sys.argv[0]))
     print("Usage: add_version.py input_path output_path version.")
     exit(-1)

  #print("path = %s\n" % (sys.argv[1]))
  
  add_version(sys.argv[1], sys.argv[2], sys.argv[3])

