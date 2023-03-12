import sys
import re
from collections import defaultdict
from math import log10

"""
	The following class is basically a struct to store cached values count,
	probability, and backoff weight for a given word.
"""
class Gram(object):
	def __init__(self):
		self.count       = 0
		self.probability = 0.0
		self.backoff     = 0.0


def getEmptyGramDict():
	# added dummy value so dictionary[1] gives unigrams, dictionary[2]
	# gives bigrams, and dictionary[3] gives trigrams.
	return [None, defaultdict(Gram), defaultdict(lambda: defaultdict(Gram)), defaultdict(lambda: defaultdict(lambda: defaultdict(Gram)))]


def smooth(corpus, min_count=1):
	dictionary, uni_count = populateDictionary(corpus, min_count)
	unigrams              = getGrams(1, dictionary)
	bigrams               = getGrams(2, dictionary)
	trigrams              = getGrams(3, dictionary)
	print 'Estimating probabilities'
	dictionary            = estimateProbs(unigrams, bigrams, trigrams, dictionary, uni_count)
	# for word1 in dictionary[2].keys():
	# 	sum = 0.0
	# 	for word2 in dictionary[2][word1].keys():
	# 		sum += dictionary[2][word1][word2].probability
	# 	if sum != 1:
	# 		print "paths following " + word1 + " do not add up to 1"
	return dictionary, unigrams, bigrams, trigrams


def smoothAndPrint(corpus, arpa, min_count):
	dictionary, unigrams, bigrams, trigrams = smooth(corpus, min_count)
	print 'Estimating backoffs'
	dictionary                              = estimateBOs(unigrams, bigrams, dictionary)
	printArpa(arpa, unigrams, bigrams, trigrams, dictionary)


def populateDictionary(corpus, min_count=1, quiet=False):
	dictionary = getEmptyGramDict()
	uni_count  = 0
	
	# handle both file and string input to create a more robust library
	if type(corpus) == file:
		lines = []
		line  = corpus.readline()
		while line:
			lines.append(line)
			line = corpus.readline()
	elif type(corpus) == str:
		lines = corpus.splitlines()
	
	unigrams = dict()
	print 'Counting unigrams'
	for line in lines:
		# capitalize everything and add beginning / end of sentence symbols
		line     = ' '.join(('<s>', line.strip(), '</s>'))
		wordList = line.split()
		
		# get unigram counts
		for i in range(len(wordList)):
			gram = wordList[i]
			if gram in unigrams:
				unigrams[gram] += 1
			else:
				unigrams[gram] = 1
		import operator
	
	print 'Sorting'
	sorted_unigrams = sorted(unigrams.iteritems(), key=operator.itemgetter(1))
	unigrams        = []
	
	print 'Adjusting'
	n    = 0
	stop = None
	for gram, count in sorted_unigrams:
		if n == 20000:
			break
		unigrams.append(gram)
		dictionary = setCount(entry=gram, count=count, dictionary=dictionary)
		uni_count += count
	print 'Counting bigrams and trigrams'
	for line in lines:
		# capitalize everything and add beginning / end of sentence symbols
		line     = ' '.join(('<s>', line.strip(), '</s>'))
		wordList = line.split()
		
		for n in range(2,4):
			for i in range(len(wordList) - n + 1):
				for word in wordList[i:i+n]:
					if word not in unigrams:
						stop = True
						break
				if stop:
					stop = None
					continue
				gram                  = tuple(wordList[i:i+n])
				dictionary, uni_count = insertGram(entry=gram, dictionary=dictionary, uni_count=uni_count)
	
	# if min_count > 1:
	# 	removed = 0
	# 	for unigram in getGrams(1, dictionary):
	# 		count = getCount(unigram, dictionary)
	# 		if count < min_count:
	# 			uni_count -= count
	# 			dictionary = removeGram(unigram, dictionary)
	# 			removed += 1
	# 	if quiet == False:
	# 		print 'Ignoring ' + str(removed) + ' unigrams'
		
	# 	removed = 0
	# 	for bigram in getGrams(2, dictionary):
	# 		if getCount(bigram, dictionary) < min_count:
	# 			dictionary = removeGram(bigram, dictionary)
	# 			removed += 1
	# 	if quiet == False:
	# 		print 'Ignoring ' + str(removed) + ' bigrams'
		
	# 	removed = 0
	# 	for trigram in getGrams(3, dictionary):
	# 		if getCount(trigram, dictionary) < min_count:
	# 			dictionary = removeGram(trigram, dictionary)
	# 			removed += 1
	# 	if quiet == False:
	# 		print 'Ignoring ' + str(removed) + ' trigrams'
	
	return dictionary, uni_count


def estimateProbs(unigrams, bigrams, trigrams, dictionary, uni_count):
	# unigrams
	for unigram in unigrams:
		probability = float(getCount(unigram, dictionary)) / uni_count
		dictionary  = setProb(unigram, probability, dictionary)
	
	# bigrams
	for bigram in bigrams:
		entry = bigram.split()
		
		# get N1+ term (unique instances after w1 of bigram)
		w2s    = getNextGrams(entry[0], dictionary)
		n1plus = len(w2s)
		
		# get unigram count of w1 and multiply by n1plus to get probability denominator
		w1count     = getCount(entry[0], dictionary)
		dictionary  = setProb(entry, float(getCount(entry, dictionary)) / float(w1count + n1plus), dictionary)
	
	# trigrams
	for trigram in trigrams:
		entry = trigram.split()
		
		# get N1+ term (unique instances after w1+w2 of trigram)
		w3s    = getNextGrams((entry[0], entry[1]), dictionary)
		n1plus = len(w3s)
		
		# get bigram count of (w1,w2) and multiply by n1plus to get probability denominator
		w1w2count   = getCount((entry[0], entry[1]), dictionary)
		probability = float(getCount(entry, dictionary)) / float(w1w2count + n1plus) #+ n1plus * getProb((entry[1], entry[2]), dictionary)) / float(w1w2count + n1plus)
		dictionary  = setProb(entry, probability, dictionary)
	return dictionary


def estimateBOs(unigrams, bigrams, dictionary):
	# unigrams
	for unigram in unigrams:
		# get N1+ term (# unique words after w1 of bigram)
		nextGrams = getNextGrams(unigram, dictionary)
		n1plus    = len(nextGrams)
		
		numerator   = 1.0
		denominator = 1.0
		for nextGram in nextGrams:
			bigram       = ' '.join((unigram, nextGram))
			numerator   -= getProb(bigram, dictionary)
			denominator -= getProb(nextGram, dictionary)
		
		# set backoff
		dictionary = setBO(unigram, numerator / denominator, dictionary)
	
	# bigrams
	for bigram in bigrams:
		# get N1+ term (# unique words after w1,w2 of trigram)
		nextGrams = getNextGrams(bigram, dictionary)
		n1plus    = len(nextGrams)
		
		numerator   = 1.0
		denominator = 1.0
		for nextGram in nextGrams:
			trigram      = ' '.join((bigram, nextGram))
			numerator   -= getProb(trigram, dictionary)
			denominator -= getProb((bigram.split()[1], nextGram), dictionary)
		
		# set backoff
		dictionary = setBO(bigram, numerator / denominator, dictionary)
	return dictionary


# print an ARPA based on the dictionary contents
def printArpa(out_file, unigrams, bigrams, trigrams, dictionary):
	f  = open(out_file, 'w')
	cf = open(out_file + '.counts', 'w')
	
	# write header
	f.write(''.join(('\\data\\\nngram 1=', str(len(unigrams)), '\nngram 2=', str(len(bigrams)), '\nngram 3=', str(len(trigrams)), '\n\n')))
	
	# write unigrams
	f.write('\\1-grams:\n')
	for unigram in unigrams:
		prob = getProb(unigram, dictionary)
		boff = getBO(unigram, dictionary)
		try:
			f.write(' '.join((toLogStr(prob,6), unigram, toLogStr(boff,6))) + '\n')
		except:
			print unigram, ' : error occurred ( prob =', prob, ') ( boff =', boff, ')'
			raise
		cf.write(str(getCount(unigram, dictionary)) + '\n')
	
	# write bigrams
	f.write('\n\\2-grams:\n')
	for bigram in bigrams:
		prob = getProb(bigram, dictionary)
		boff = getBO(bigram, dictionary)
		try:
			f.write(' '.join((toLogStr(getProb(bigram, dictionary),6), bigram, toLogStr(getBO(bigram, dictionary),6))) + '\n')
		except:
			print bigram, ' : error occurred ( prob =', prob, ') ( boff =', boff, ')'
			raise
		cf.write(str(getCount(bigram, dictionary)) + '\n')
	
	# write trigrams
	f.write('\n\\3-grams:\n')
	for trigram in trigrams:
		prob = getProb(trigram, dictionary)
		boff = getBO(trigram, dictionary)
		try:
			f.write(' '.join((toLogStr(getProb(trigram, dictionary),6), trigram)) + '\n')
		except:
			print trigram, ' : error occurred ( prob =', prob, ') ( boff =', boff, ')'
			raise
		cf.write(str(getCount(trigram, dictionary)) + '\n')
	
	f.write('\n\\end\\\n\n')
	cf.close()


"""
	This python script is an implementation of witten bell smoothing
	that takes a text corpus as an input and outputs a language model
	in the ARPA-MIT LM format (see http://www.ee.ucla.edu/~weichu/htkbook/node243_ct.html
	if you need any additional references on this format).
	
	usage: python wbSmooth.py <input corpus> <output arpa>
"""
def main(argv):
	if len(argv) < 3:
		print "usage: python wbsmooth.py <input corpus> <output arpa> [<min_count>]"
		sys.exit()
	
	with open(argv[1], 'r') as f:
		smoothAndPrint(f, argv[2], int(argv[3]) if len(argv) > 3 else 1)


"""
	utility functions for dictionary

	These all accept either strings or tuples/lists (1 word per index) as arguments
"""
def insertGram(entry, dictionary, uni_count):
	if isinstance(entry, str):
		entry = entry.split()

	n = len(entry)

	if n == 1:
		dictionary[n][entry[0]].count += 1
		uni_count += 1
	elif n == 2:
		dictionary[n][entry[0]][entry[1]].count += 1
	elif n == 3:
		dictionary[n][entry[0]][entry[1]][entry[2]].count += 1
	
	return dictionary, uni_count


def removeGram(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		dictionary[n].pop(entry[0], None)
	elif n == 2:
		dictionary[n][entry[0]].pop(entry[1], None)
	else:
		dictionary[n][entry[0]][entry[1]].pop(entry[2], None)
	return dictionary


def getCount(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		return dictionary[n][entry[0]].count
	if n == 2:
		return dictionary[n][entry[0]][entry[1]].count
	return dictionary[n][entry[0]][entry[1]][entry[2]].count


def setCount(entry, count, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		dictionary[n][entry[0]].count = count
	elif n == 2:
		dictionary[n][entry[0]][entry[1]].count = count
	else:
		dictionary[n][entry[0]][entry[1]][entry[2]].count = count
	return dictionary


def getGrams(n, dictionary):
	grams = []
	
	if n == 1:
		grams = dictionary[n].keys()
	elif n == 2:
		w1s = dictionary[n].keys()
		for w1 in w1s:
			w2s = dictionary[n][w1].keys()
			for w2 in w2s:
				grams.append(' '.join((w1,w2)))
	elif n == 3:
		w1s = dictionary[n].keys()
		for w1 in w1s:
			w2s = dictionary[n][w1].keys()
			for w2 in w2s:
				w3s = dictionary[n][w1][w2].keys()
				for w3 in w3s:
					grams.append(' '.join((w1,w2,w3)))
	return sorted(grams)


def getNextGrams(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		return dictionary[2][entry[0]].keys()
	if n == 2:
		return dictionary[3][entry[0]][entry[1]].keys()


def setProb(entry, prob, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		dictionary[n][entry[0]].probability = prob
	elif n == 2:
		dictionary[n][entry[0]][entry[1]].probability = prob
	elif n == 3:
		dictionary[n][entry[0]][entry[1]][entry[2]].probability = prob
	return dictionary


def getProb(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		return dictionary[n][entry[0]].probability
	if n == 2:
		if entry[1] in dictionary[n][entry[0]]:
			return dictionary[n][entry[0]][entry[1]].probability
		else:
			return float(getBO(entry[0], dictionary)) * getProb(entry[1], dictionary)
	return dictionary[n][entry[0]][entry[1]][entry[2]].probability


def setBO(entry, bo, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		dictionary[n][entry[0]].backoff = bo
	elif n == 2:
		dictionary[n][entry[0]][entry[1]].backoff = bo
	elif n == 3:
		dictionary[n][entry[0]][entry[1]][entry[2]].backoff = bo
	return dictionary


def getBO(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		return dictionary[n][entry[0]].backoff
	if n == 2:
		return dictionary[n][entry[0]][entry[1]].backoff
	return dictionary[n][entry[0]][entry[1]][entry[2]].backoff


def getGramStats(entry, dictionary):
	if isinstance(entry, str):
		entry = entry.split()
	
	n = len(entry)
	
	if n == 1:
		return dictionary[n][entry[0]].count, dictionary[n][entry[0]].probability, dictionary[n][entry[0]].backoff
	if n == 2:
		return dictionary[n][entry[0]][entry[1]].count, dictionary[n][entry[0]][entry[1]].probability, dictionary[n][entry[0]][entry[1]].backoff
	return dictionary[n][entry[0]][entry[1]][entry[2]].count, dictionary[n][entry[0]][entry[1]][entry[2]].probability, dictionary[n][entry[0]][entry[1]][entry[2]].backoff


# for printing purposes
def toLogStr(x, sigfigs):
	if x == 0:
		return '-99'
	try:
		temp = log10(x)
	except:
		print x
		raise
	
	if temp > -1.0:
		return str(round(temp, sigfigs))
	else:
		return str(round(temp, sigfigs-1))


if __name__ == '__main__':
	main(sys.argv)
