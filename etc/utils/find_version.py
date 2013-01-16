import sys

def find_version(path):

    fd = open(path)

    for line in fd:
        index = line.find("GMVAULT_VERSION = \"")
        if index > -1:
            print(line[index+19:-2])
            res = line[index+19:-2]
            return res.strip()

    raise Exception("Cannot find GMVAULT_VERSION in %s\n" % (path))


if __name__ == '__main__':

  if len(sys.argv) < 2:
     print("Error: Need the path to gmv_cmd.py")
     exit(-1)

  #print("path = %s\n" % (sys.argv[1]))
  
  find_version(sys.argv[1])

