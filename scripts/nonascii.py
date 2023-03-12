import sys
out = open(sys.argv[2],'w')
for character in set(i for i in open(sys.argv[1], 'r').read() if ord(i) > 128): out.write(character + '\n')
out.close()

