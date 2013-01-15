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

VERSION_PATTERN = r'###VERSION###' 
VERSION_RE      = re.compile(VERSION_PATTERN)

def add_version(a_input, a_output):
    """
	"""
    f = open(a_input)
	for line in f:
	   VE

if __name__ == '__main__':

  if len(sys.argv) < 3:
     print("Error: Need the path to gmv_cmd.py")
     exit(-1)

  #print("path = %s\n" % (sys.argv[1]))
  
  #find_version(sys.argv[1])
  add_version(sys.argv[1], sys.argv[2])

