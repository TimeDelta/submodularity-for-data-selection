import sys, re, optparse, os
from collections import defaultdict
from math import log10
import wbsmooth as wb
from os.path import isfile

from sys import platform as _platform
if _platform == 'win32':
	import winsound


# corpus can be either a string or a file
# clusters can be either a clusters dictionary or a list of files
def createPreclusteredLM(corpus, clusters, arpa):
	# read the corpus
	if type(corpus) == file:
		input = open(corpus, 'r')
		text  = input.read()
		input.close()
	else:
		text = corpus
	
	# substitute the clusters into the text
	predefinedClusters, text = substituteClusters(clusters, text)
	
	# count n-grams and perform Witten-Bell smoothing
	dictionary, unigrams, bigrams, trigrams = wb.smooth(text)
	
	# expand cluster n-grams
	dictionary = expandDictionaryWithClusters(unigrams, bigrams, trigrams, predefinedClusters, dictionary)
	
	# estimate backoffs
	unigrams   = wb.getGrams(1, dictionary)
	bigrams    = wb.getGrams(2, dictionary)
	dictionary = wb.estimateBOs(unigrams, bigrams, dictionary)
	
	# output ARPA file
	wb.printArpa(arpa, wb.getGrams(1, dictionary), wb.getGrams(2, dictionary), wb.getGrams(3, dictionary))


def substituteClusters(clusters, text):
	if type(clusters) == list:
		predefinedClusters = dict()
		precluster_re      = re.compile('^@![a-zA-Z0-9_\']+$')
		word_re            = re.compile('^[a-zA-Z0-9_\']+$')
		for clusterfile in clusters:
			classes        = open(clusterfile, 'r')
			currentCluster = ''
			
			for line in classes:
				line = re.sub('\r|\n', '', line)
				if precluster_re.match(line):
					# add a new cluster
					predefinedClusters[line] = []
					currentCluster           = line
				elif word_re.match(line):
					# add new word to current cluster
					predefinedClusters[currentCluster].append(line)
					
					# replace all occurrences of the word with the current cluster name
					text = re.sub('(((?<!\')(?<!@)(?<!!))|^)' + r'\b' + line + r'\b' + '(?!\')', currentCluster, text)
			
			classes.close()
	elif type(clusters) == dict:
		for cluster, words in clusters.iteritems():
			for word in words:
				text = re.sub('(((?<!\')(?<!@)(?<!!))|^)' + r'\b' + word + r'\b' + '(?!\')', cluster, text)
		predefinedClusters = clusters
	else:
		raise ValueError('The clusters argument must be either a list of files or a clusters dictionary.')
	return predefinedClusters, text


def expandDictionaryWithClusters(unigrams, bigrams, trigrams, predefinedClusters, dictionary):
	precluster_re = re.compile('^@![a-zA-Z0-9_\']+$')
	word_re       = re.compile('^[a-zA-Z0-9_\']+$')
	newDict       = wb.getEmptyGramDict()
	for n in range(1,4):
		if n == 1:
			grams = unigrams
		elif n == 2:
			grams = bigrams
		elif n == 3:
			grams = trigrams
		for entry in grams:
			# enumerate possibilities for each slot
			possibilities = [[],[],[]]
			i             = 0
			# words         = []
			for word in entry.split():
				# words.append(word)
				if precluster_re.match(word):
					possibilities[i] = predefinedClusters[word]
				else:
					possibilities[i] = [word]
				i += 1
			
			# if (possibilities[0] > 1 and possibilities[1] > 1) or (possibilities[1] > 1 and possibilities[2] > 1):
			# 	print ' '.join(words)
			
			# enumerate every combination of possibilities from each slot
			expansions = possibilities[0]
			for i in range(1,n):
				new_expansions = []
				for original_expansion in expansions:
					for k in range(len(possibilities[i])):
						possibility = possibilities[i][k]
						new_expansions.append(original_expansion + ' ' + possibility)
				expansions = new_expansions
			
			# set the stats for every expansion
			count, probability, backoff = wb.getGramStats(entry, dictionary)
			probability /= len(expansions)
			for expansion in expansions:
				newDict = wb.setProb(expansion, probability, newDict)
				newDict = wb.setBO(expansion, backoff, newDict)
				newDict = wb.setCount(expansion, count, newDict)
	return newDict


def split_files(option, opt, value, parser):
	setattr(parser.values, option.dest, value.split(','))


"""
	MAIN
"""
def main():
	columns = 80
	fmt     = optparse.IndentedHelpFormatter(max_help_position=7, width=int(columns))
	parser  = optparse.OptionParser(usage='', formatter=fmt)
	
	# add options to option parser
	parser.add_option('-c', '--corpus',
	                  help     = 'Corpus file to use. ["corpus"]')
	parser.add_option('-p', '--predefined',
	                  type     = 'string',
	                  action   = 'callback',
	                  callback = split_files,
	                  help     = 'List of files containing pre-defined clusters to use.')
	parser.add_option('-n', '--num-clusters',
	                  type     = 'int',
	                  help     = 'The number of clusters to use in the clustering algorithm. 0 means no use of the clustering algorithm. [0]')
	parser.add_option('-o', '--output',
	                  help     = 'File name for the resulting ARPA file (writes to <argument>.arpa). ["output"]')
	parser.add_option('-w', '--write-clusters',
	                  action   = 'store_true',
	                  help     = 'Write the clusters to a file(<corpus file name>.clusters).')
	parser.add_option('-q', '--quiet',
	                  action   = 'store_true',
	                  help     = 'Quiet mode.')
	
	parser.set_defaults(corpus         = 'corpus',
	                    predefined     = None,
	                    num_clusters   = None,
	                    check          = None,
	                    output         = 'output',
	                    write_clusters = None,
	                    quiet          = None)
	options, args = parser.parse_args()
	
	if not options.predefined and not options.num_clusters:
		print 'Must specify either cluster files to use or the number of clusters to create.'
		exit(1)
	
	# get the corpus text
	try:
		corpus = open(options.corpus, 'r')
		text   = corpus.read()
		corpus.close()
	except IOError:
		print 'Error: Cannot read corpus.'
		exit(1)
	
	# substitute the clusters into the text
	if not options.quiet:
		print 'Substituting pre-defined clusters'
	if options.predefined:
		predefinedClusters, text = substituteClusters(options.predefined, text)
		if options.num_clusters:
			# write to file b/c wcluster takes file input
			tempfile = open('wclustertempfile', 'w')
			tempfile.write(text)
			tempfile.close()
	
	if options.num_clusters:
		if not options.quiet:
			print 'Creating ' + str(options.num_clusters) + ' clusters'
		# perform clustering according to current platform
		if _platform == 'win32':
			command = 'wcluster_win'
		elif _platform == 'darwin':
			command = './wcluster_darwin'
		elif _platform == 'linux' or _platform == 'linux2':
			command = './wcluster_linux'
		else:
			print 'Cannot determine correct wcluster executable for current platform. Please specify location:'
		command += ' --ncollocs 0 --text '
		if options.predefined:
			command += 'wclustertempfile'
		else:
			command += options.corpus
		command += ' --paths temp-paths --c ' + str(options.num_clusters)
		os.system(command)
		
		# open the paths file generated by wcluster
		input = open('temp-paths', 'r')
		
		# create a dictionary to store the words in each cluster
		clusters = dict()
		
		# read in the newly created clusters
		for line in input:
			line = line.split()
			path = line[0]
			word = line[1]
			
			done = False
			for key, value in clusters.iteritems():
				# if the current cluster's path == the new word's path, add the new word
				# to the current cluster
				if key == path:
					# log progress if requested
					if options.quiet == False:
						msg = 'Merging "' + word + '" with cluster ' + key + ' (# Clusters = ' + str(len(clusters)) + ')'
						if log:
							log.write(msg + '\n')
						else:
							print msg
					
					clusters[key].append(word)
					done = True
					break
			
			if done == False:
				# create a new cluster
				clusters[path] = [word]
				
				# log progress if requested
				if options.quiet == False:
					msg = 'Creating new cluster: ' + path + ': ' + word + ' (# Clusters = ' + str(len(clusters)) + ')'
					if log:
						log.write(msg + '\n')
					else:
						print msg
		input.close()
		
		# replace 
		for key, value in clusters.iteritems():
			for word in value:
				# log progress if requested
				if options.quiet == False:
					msg = 'Replacing ' + word
					if log:
						log.write(msg + '\n')
					else:
						print msg
				
				if word[0:2] == '@!':
					text = re.sub(word, key, text)
				else:
					text = re.sub('(((?<!\')(?<!@)(?<!!))|^)' + r'\b' + word + r'\b' + '(?!\')', key, text)
		
		# delete all intermediate files created by wcluster
		os.system('rm -f temp-paths ' + options.input + '.int ' + options.input + '.strdb')
		os.system('rm -rf ' + options.input + '*.out')
		if options.predefined:
			os.system('rm -f wclustertempfile*')
	
	# count n-grams and perform Witten-Bell smoothing
	if not options.quiet:
		print 'Smoothing'
	dictionary, unigrams, bigrams, trigrams = wb.smooth(text)
	
	# expand cluster n-grams
	if not options.quiet:
		print 'Expanding clusters'
	dictionary = expandDictionaryWithClusters(unigrams, bigrams, trigrams, predefinedClusters, dictionary)
	
	# estimate backoffs
	if not options.quiet:
		print 'Estimating backoffs'
	unigrams   = wb.getGrams(1, dictionary)
	bigrams    = wb.getGrams(2, dictionary)
	dictionary = wb.estimateBOs(unigrams, bigrams, dictionary)
	
	# output ARPA file
	if not options.quiet:
		print 'Printing ARPA file'
	wb.printArpa(options.output + '.arpa', unigrams, bigrams, wb.getGrams(3, dictionary), dictionary)
	
	# alert user that script has finished by playing sound
	if _platform == 'linux' or _platform == 'linux2':
		try:
			os.sytem('play --no-show-progress --null --channels 1 synth %s sine %f' %(300,2000))
		except:
			sys.stdout.write('\a')
	elif _platform == 'win32':
		winsound.Beep(300, 2000)
	elif _platform == 'darwin':
		os.system('say "finished creating ARPA file"')
	exit(0)


if __name__ == '__main__':
	main()
