import operator
import random

n = 3

#generates a (n word tuple: count) dictionary from a list of
#text files.  text files must be only alphabetic characters 
#and white space
def getCounts(fileList):
	ngrams = {}
	
	for file in fileList:
		f = open(file)
		line = f.readline()
		while line:
			line = line.rstrip()
			wordList = line.split()
			
			for i in range(len(wordList) - n + 1):
				gram = tuple(wordList[i:i+n])
				
				if gram in ngrams:
					ngrams[gram] += 1
				else:
					ngrams[gram] = 1
			
			line = f.readline()
		f.close()
	return ngrams
	
#returns a list of dictionary elements as a sorted list by key
def outputNgram(outFile, dict):
	f = open(outFile, 'w')
	sortedDict = sorted(dict.iteritems(), key=operator.itemgetter(1), reverse=True)
	
	for entry in sortedDict:
		outstr = ' '.join((str(entry[1]), '-', ' '.join(entry[0]), '\n'))
		f.write(outstr)
	
	f.close()

#returns an integer representing the total count of all n-grams
def getTotalCount(dict):
	sortedDict = sorted(dict.iteritems(), key=operator.itemgetter(1), reverse=True)
	ct = 0
	
	for entry in sortedDict:
		ct = ct + entry[1]
	
	return ct
	

#selects a random key from a dictionary, weighted by the values.
#values must be integers.
def weightedRandom(dict):
	r = random.uniform(0, sum(dict.itervalues()))
	s = 0.0
	for k, w in dict.iteritems():
		s += w
		if r < s: return k
	return k