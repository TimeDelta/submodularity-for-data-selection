import sys
f = open(sys.argv[1], 'r')
backoffs = 1
s = set()
for line in f:
	if line.startswith('\\3'):
		backoffs = 0
		entry    = line.strip().split()
		entry    = ' '.join(entry[1:len(entry)-backoffs])
		if entry in s:
			print entry
		s.add(entry)
