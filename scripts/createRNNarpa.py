import sys, os, optparse, random, re
from sys import platform as _platform
if _platform == 'win32':
	import winsound

def split_corpus(corpus, training, validation, ratio, quiet):
	# tell the user what's happening
	if not quiet:
		print 'Randomly splitting corpus'
	
	# use the "/tmp" directory to store the training and validation data sets
	training   = '/tmp/' + training
	validation = '/tmp/' + validation
	
	sentences = []
	sentence_count = 0;
	
	infile = open(corpus, 'r')
	for line in infile:
		if line:
			sentences.append(line)
			sentence_count += 1
	infile.close()
	
	if not quiet:
		print 'Total Sentence Count: ' + str(sentence_count)
	
	# seed the random number generator
	random.seed()
	
	# open output files
	trainfile = open(training, 'w')
	validfile = open(validation, 'w')
	
	# faster to pick the sentences to add to training set
	if options.ratio < .5:
		training_sentence_count   = int(options.ratio * sentence_count)
		training_sentence_indices = random.sample(xrange(sentence_count), training_sentence_count)
		
		if not quiet:
			print 'Training Sentence Count: ' + str(training_sentence_count)
		
		# remove the training sentences in reverse order to avoid changing the index for each chosen sentence
		for i in reversed(training_sentence_indices):
			trainfile.write(sentences.pop(i) + '\n')
		
		if not quiet:
			print 'Validation Sentence Count: ' + str(len(sentences))
		
		# output the validation set
		for sentence in sentences:
			validfile.write(sentence + '\n')
	# faster to pick the sentences to add to validation set
	else:
		validation_sentence_count   = int((1 - options.ratio) * sentence_count)
		validation_sentence_indices = random.sample(xrange(sentence_count), validation_sentence_count)
		validation_sentence_indices.sort()
		
		if not quiet:
			print 'Validation Sentence Count: ' + str(validation_sentence_count)
		
		# remove the validation sentences in reverse order to avoid changing the index for each chosen sentence
		for i in reversed(validation_sentence_indices):
			validfile.write(sentences.pop(i) + '\n')
		
		if not quiet:
			print 'Training Sentence Count: ' + str(len(sentences))
		
		# output the validation set
		for sentence in sentences:
			trainfile.write(sentence + '\n')
	
	trainfile.close()
	validfile.close()



if __name__ == '__main__':
	usage = """python createRNNarpa.py [options] [additional args for rnnlm]
A front end for creating an ARPA file by training an RNNLM,
generating a new corpus and training a backoff n-gram on it."""
	
	fmt    = optparse.IndentedHelpFormatter(max_help_position=50, width=100)
	parser = optparse.OptionParser(usage=usage, formatter=fmt)
	
	# add options to option parser
	parser.add_option('-i', '--input',                           help='Corpus file to use. ["corpus"]')
	parser.add_option('-b', '--bptt',       type='int',          help='Amount of steps to propagate error back in time. [10]')
	parser.add_option('-w', '--words',      type='int',          help='Number of words to generate for the new corpus. [1000000]')
	parser.add_option('-r', '--ratio',      type='float',        help='The ratio of the input sentences to keep for the training set. [.75]')
	parser.add_option('-s', '--seeds',      type='int',          help='The number of times to train with different random seed values, then interpolate. [5]')
	parser.add_option('-n', '--hidden',     type='int',          help='The number of hidden neurons to use. [125]')
	parser.add_option('-k', '--keep',       action='store_true', help='Keep the resulting RNNLM file and corpus file.')
	# parser.add_option('-a', '--algorithm',                       help='The type of algorithm to use when creating the backoff n-gram ARPA file.')
	parser.add_option('-t', '--train',                           help='The training set to use. Ignores -i and -r arguments. Must supply -v argument.')
	parser.add_option('-v', '--valid',                           help='The validation set to use. Ignores -i and -r arguments. Must supply -t argument.')
	parser.add_option('-1', '--one-iter',   action='store_true', help='Will cause training to perform exactly one iteration over training data. This implies "-r 1".')
	parser.add_option('-q', '--quiet',      action='store_true', help='Quiet mode.')
	
	parser.set_defaults(input='corpus', bptt=10, ratio=.75, words=1000000, seeds=5, hidden=125, one_iter=None, quiet=None, keep=None)
	options, args = parser.parse_args()
	
	args = ' '.join(args)
	
	# make sure the specified corpus file can be opened
	try:
		file_exists = open(options.input, 'r')
		file_exists.close()
	except:
		print 'Cannot open corpus file.'
		exit()
	
	# make sure that seeds is >= 1
	if options.seeds < 1:
		print 'Cannot have a seeds parameter < 1.'
		exit()
	
	# make sure that number of hidden neurons is >= 1
	if options.hidden < 1:
		print 'Cannot have < 1 hidden neurons.'
		exit()
	
	# make sure words >= 1
	if options.words < 1:
		print 'Cannot create a corpus with < 1 words.'
		exit()
	
	# split the corpus if requested
	if options.ratio < 1 and not options.one_iter:
		trainingset   = 'train' + str(options.ratio)[1:]
		validationset = 'valid' + str(1 - options.ratio)[1:]
		rnnlm         = trainingset
		split_corpus(options.input, trainingset, validationset, options.ratio, options.quiet)
	else:
		trainingset   = None
		validationset = None
		if options.one_iter:
			rnnlm = 'one-iter'
		else:
			rnnlm = 'same'
	rnnlm += '_bptt' + str(options.bptt) + '_hidden' + str(options.hidden) + '_seeds' + str(options.seeds)
	
	rnnlmfile          = rnnlm + '.rnnlm'
	description        = rnnlm + '_words' + str(options.words)
	rnnlm_base_command = './rnnlm -class 1 -min-improvement 1 -bptt ' + str(options.bptt) + args + ' -train '
	if options.ratio == 1:
		if not options.one_iter:
			rnnlm_base_command += options.input + ' -valid ' + options.input
		else:
			rnnlm_base_command += ' -one-iter'
	else:
		rnnlm_base_command += '/tmp/' + trainingset + ' -valid /tmp/' + validationset
	rnnlm_base_command += ' -rand-seed ' + str(random.randint(0, 999999999)) + ' -hidden ' + str(options.hidden) + ' -rnnlm '
	
	if options.seeds > 1:
		# generate the specified number of RNNLMs to be interpolated
		rnnlm_files = []
		for i in range(0, options.seeds):
			random.jumpahead(random.randint(0, 999999999))
			# tmpfile = '/tmp/' + str(i) + rnnlmfile
			tmpfile = str(i) + rnnlmfile
			command = re.sub('-rand-seed [0-9]+\s', '-rand-seed ' + str(random.randint(0, 999999999)) + ' ', rnnlm_base_command) + tmpfile
			if not options.quiet:
				print 'Training RNNLM number ' + str(i + 1)
			else:
				command += ' > /tmp/junk'# /tmp/junk is deleted later in the script (after ARPA file is written)
			os.system(command)
			
			# remove the log file created
			os.system('rm -f ' + tmpfile + '.output.txt')
			
			# keep track of the tmp files created
			rnnlm_files.append(tmpfile)
		
		outfile         = open(rnnlmfile, 'w')
		hidden_layer_re = re.compile('^Hidden layer activation:$')
		
		# read in and store all of the lines after the header for each file
		tmpfiles = []
		lines    = []
		for i in range(0, len(rnnlm_files)):
			lines.append([])
			tmpfile = open(rnnlm_files[i], 'r')
			start = None
			for line in tmpfile:
				if i == 0:
					outfile.write(re.sub('\n', '', line) + '\n')
				if hidden_layer_re.match(line):
					start = True
				if start:
					lines[i].append(line)
			tmpfile.close()
		
		# interpolate
		if not options.quiet:
			print 'Interpolating trained RNNLMs'
		number_line_re  = re.compile('^-?[0-9]+(\.[0-9]+)?$')
		running_total   = 0
		LAST_FILE_INDEX = options.seeds - 1
		for i in range(0, len(lines[0])):
			for line_list in lines:
				line = line_list[i]
				if number_line_re.match(line):
					if i == 0:
						running_total = 0
					else:
						running_total += float(re.sub('\n', '', line))
						if i == LAST_FILE_INDEX:
							running_total /= options.seeds
							outfile.write(str(running_total) + '\n')
				elif i == 0:
					outfile.write(line + '\n')
		# line = 'dummy value'
		# running_total = 0
		# LAST_FILE_INDEX = options.seeds - 1
		# while line:
		# 	for i in range(0, len(tmpfiles)):
		# 		for line in tmpfiles[i]:
		# 			if number_line_re.match(line):
		# 				if i == 0:
		# 					running_total = 0
		# 				else:
		# 					running_total += float(re.sub('\n', '', line))
		# 					if i == LAST_FILE_INDEX:
		# 						running_total /= options.seeds
		# 						outfile.write(str(running_total) + '\n')
		# 			elif i == 0:
		# 				outfile.write(line + '\n')
		# 			break
		
		# close the tmp files
		for i in range(0, len(tmpfiles)):
			tmpfiles[i].close()
		
		# clean up temporary RNNLM files
		# for tmpfile in rnnlm_files:
		# 	os.system('rm -f ' + tmpfile)
	else:
		command = rnnlm_base_command + rnnlmfile
		if not options.quiet:
			print 'Training RNNLM'
		else:
			command += ' > /tmp/junk'# /tmp/junk is deleted later in the script (after ARPA file is written)
		os.system(command)
		
		# remove the log file created
		os.system('rm -f ' + tmpfile + '.output.txt')
	
	# delete training set and validation set only if the original corpus was split
	if trainingset:
		os.system('rm -f /tmp/' + trainingset)
	if validationset:
		os.system('rm -f /tmp/' + validationset)
	
	# generate new corpus file
	if not options.quiet:
		print 'Generating new corpus'
	os.system('./rnnlm -rnnlm ' + rnnlmfile + ' -gen ' + str(options.words) + ' > ' + description + '.corpus')
	
	# remove the first two lines in the new corpus file b/c they're junk
	if not options.quiet:
		print 'Cleaning generated corpus'
	os.system('tail -n +3 ' + description + '.corpus > tempfile')
	os.system('mv tempfile ' + description + '.corpus')
	
	# create Witten-Bell (backoff) smoothed ARPA file
	if not options.quiet:
		print 'Performing Witten-Bell (backoff) smoothing'
		os.system('python wbsmooth.py ' + description + '.corpus ' + description + '.trigram.arpa')
	else:
		os.system('python wbsmooth.py ' + description + '.corpus ' + description + '.trigram.arpa > /tmp/junk')
		os.system('rm -f /tmp/junk')
	
	if not options.keep:
		os.system('rm -f ' + rnnlmfile)
		os.system('rm -f ' + description + '.corpus')
	
	# alert user that script has finished by playing sound
	if _platform == 'linux' or _platform == 'linux2':
		# try:
		# 	os.sytem('play --no-show-progress --null --channels 1 synth %s sine %f' %(300,2000))
		# except:
		sys.stdout.write('\a')
	elif _platform == 'win32':
		winsound.Beep(300, 2000)
	elif _platform == 'darwin':
		os.system('say "finished creating ARPA file"')
	
	exit()
