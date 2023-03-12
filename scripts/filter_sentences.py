#!/usr/bin/python
import sys

# ensure minimum version of python
major = sys.version_info[0]
middle = sys.version_info[1]
minor = sys.version_info[2]
if major < 2 or (major == 2 and middle < 7) or (major == 2 and middle == 7 and minor < 3):
    print("This script requires a minimum Python version of 2.7.3")
    sys.exit(1)

import os, random, operator
from math import log, log10
from sys import stdin, stderr


#generates a (n word tuple: count) dictionary from a list of
#text files.  text files must be only alphabetic characters 
#and white space
def getCounts(f, n):
	ngrams = {}
	total  = 0
	with open(f) as f:
		line = f.readline()
		while line:
			line  = line.rstrip()
			words = line.split()
			
			for i in range(len(words) - n + 1):
				gram = tuple(words[i:i+n])
				if gram in ngrams:
					ngrams[gram] += 1
				else:
					ngrams[gram] = 1
			
			total += len(words)
			line = f.readline()
	return ngrams


#returns an integer representing the total count of all n-grams
def getTotalCount(dict):
	sortedDict = sorted(dict.iteritems(), key=operator.itemgetter(1), reverse=True)
	ct = 0
	
	for entry in sortedDict:
		ct += entry[1]
	
	return ct


# See "Selecting relevant text subsets from web-data for building topic
# specific language models" for further reference. This algorithm is
# roughly based on one described in that research paper, but is expanded
# to filter on trigram counts rather than unigram counts.
def incrementalFilter(seed_file, tuning_parameter, n=3):
	P = getCounts(seed_file, n)
	W = getCounts(seed_file, n)
	N = getTotalCount(W) # total number of words already selected
	
	num_added = 0
	
	for sentence in stdin:
		sentence = sentence.strip()
		words = sentence.split()
		grams = {}
		
		# populate n-gram counts for the current sentence
		for j in range(len(words) - n + 1):
			gram = tuple(words[j:j+n])
			if gram in grams:
				grams[gram] += 1
			else:
				grams[gram] = 1
		
		# T1 represents the decrease in probability mass due to adding the words in the current sentence
		T1 = log10(float(N + len(words))/float(N)) + float(tuning_parameter) * float(len(words))/float(N)
		
		# T2 represents the in-domain distributionally weighted improvement in probability for the words in the current sentence
		T2 = 0.0
		for gram in grams:
			if gram in W:
				T2 += log10(float(W[gram] + grams[gram])/float(W[gram])) * float(getDictCtSafe(P,gram))
			#TODO: revisit this. it doesn't work as is, but I would like to add extra weight on oov.
			#else:
			#	#place extra weight on introducing new words to vocab
			#	T2 = T2 + 50.0
		
		if T1 < T2:
			for gram in grams:
				if gram in W:
					W[gram] += 1
				else:
					W[gram] = 1
			N += len(words)
			num_added += 1
			print sentence
	return num_added


def getDictCtSafe(dict, entry):
	if entry in dict:
		return dict[entry]
	else:
		return 0


def main():
	import optparse
	
	usage  = 'filter_sentences.py [options]\nA tool for filtering mined sentences based on relevance to seed sentences. Reads from stdin and writes to stdout.'
	parser = optparse.OptionParser(usage=usage, formatter=optparse.IndentedHelpFormatter(max_help_position=30, width=80))
	
	# add options to the option parser
	parser.add_option('-s', '--seed',
	                  default = None,
	                  help    = 'File containing in-domain seed sentences to use.')
	parser.add_option('-t', '--tuning-parameter',
	                  default = 750.0,
	                  type    = 'float',
	                  help    = 'The scalar value by which the thresholding function is multiplied. Smaller values will allow more text through. Can be negative or positive. [Default: 750]')
	
	# parse options and arguments
	options, args = parser.parse_args()
	
	# clean up
	del usage
	del parser
	
	# filter out bad sentences
	stderr.write('Added ' + str(incrementalFilter(options.seed, options.tuning_parameter)) + ' sentences\n')


if __name__ == '__main__':
	main()
