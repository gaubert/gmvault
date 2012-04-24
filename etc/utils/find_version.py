import sys

if len(sys.argv) < 2:
  print("Error: Need the path to gmv_cmd.py")
  exit(-1)

path = sys.argv[1]

fd = open(path)

for line in fd:
	index = line.find("GMVAULT_VERSION=\"")
	if index > -1:
		print(line[index+17:-2])
