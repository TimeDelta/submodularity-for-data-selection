#!/usr/bin/env python
import re, optparse

def main():
	usage = '''testregex [-m] (-f regex_file)|(<regex>) <test_cases_file>
  <regex>           : Python compatible regular expression.
  <test_cases_file> : File containing test cases.
                      Precede positive test cases with "+". Precede negative test cases with "-".
                      Everything (including whitespace) after the + or - will be taken as part of the test string.'''
	parser = optparse.OptionParser(usage=usage)
	
	# add options to the option parser
	parser.add_option('-m', '--full-match',
	                  default = None,
	                  action  = 'store_true',
	                  help    = 'The regex must match an entire test case in order to give a positive result. This option is equivalent to matching "^regex$".')
	parser.add_option('-f', '--file',
	                  default = None,
	                  help    = 'Use a file as the regex to be tested instead. This option OR\'s each line of the file together to make the final regex.')
	
	# parse options, arguments
	options, args = parser.parse_args()
	
	# clean up
	del parser
	
	if options.file:
		regex = ''
		# read the regular expression from a file
		with open(options.file, 'r') as f:
			for line in f:
				regex += '(' + line.strip() + ')|'
			regex = regex[:-1] # remove the last "|" character
			print regex
		tests_file = args[0]
	else:
		regex      = args[0]
		tests_file = args[1]
	
	if options.full_match:
		regex = '^(' + regex + ')$'
	
	# prepare the regular expression
	regex = re.compile(regex)
	
	# read in all of the test cases
	tests    = dict()
	line_num = 1
	with open(tests_file, 'r') as tests_file:
		for line in tests_file:
			line = line.strip()
			if line[0] == '+':   # positive test case
				tests[line[1:]] = True
			elif line[0] == '-': # negative test case
				tests[line[1:]] = None
			else:                # invalid test case
				print 'Error - Line ' + str(line_num) + ' (' + line + ') does not specify whether the test case is positive (+) or negative (-).'
				exit(1)
			line_num += 1
	
	# evaluate all of the test cases
	passes = 0
	fails  = []
	for test, correct_result in tests.iteritems():
		result = regex.search(test)
		if (result and correct_result) or (not result and not correct_result):
			passes += 1
		else:
			if correct_result:
				case_string = '+' + test
			else:
				case_string = '-' + test
			fails.append(case_string)
	
	# print the results
	print 'Passed   : ' + str(passes)
	print 'Failed   : ' + str(len(fails))
	print 'Accuracy : ' + str(float(passes) / len(tests) * 100) + '%'
	if len(fails) > 0:
		print '\nFailed Test Cases'
		print '-----------------'
		for test in fails:
			print test


if __name__ == '__main__':
	main()
