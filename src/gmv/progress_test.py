import time
import sys

def progress_2():
	"""
	"""
	percents = 0
	to_write = "Progress: [%s ]\r" % (percents)
	sys.stdout.write(to_write)
	sys.stdout.flush()

	steps = 100

	for i in xrange(steps):
		time.sleep(0.1)
		percents += 1
		#sys.stdout.write("\b" * (len(to_write)))
		to_write = "Progress: [%s percents]\r" % (percents)
		sys.stdout.write(to_write)
		sys.stdout.flush()



def progress_1():
	"""
	   progress_1
	"""
	toolbar_width = 100

	# setup toolbar
	sys.stdout.write("[%s]" % (" " * toolbar_width))
	sys.stdout.flush()
	sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

	for i in xrange(toolbar_width):
		time.sleep(0.1) # do real work here
		# update the bar
		sys.stdout.write("-")
		sys.stdout.flush()

	sys.stdout.write("\n")

if __name__ == '__main__':
	progress_2()
