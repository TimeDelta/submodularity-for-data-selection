import re, sys
f = open(sys.argv[1], 'r')
line_re  = re.compile(r'(?i)^((-[0-9]{1,2}\.[0-9]+( *(([a-z\']+)|(</?s>))){1,3}( *-[0-9]{1,2}(\.[0-9]+)?)?)|(\\[1-3]-grams:)|(\\end\\)|(\\data\\)|(ngram [1-3]=[0-9]+)|())\r?\n')
line_num = 1
for line in f:
	if not line_re.match(line):
		print 'Line ' + str(line_num) + ':\t' + line[:-1]
	line_num += 1
f.close()
