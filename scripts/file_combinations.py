from os.path import isfile, join, isdir
from files import listfiles
import os, optparse, re
import itertools

def main():
	rows, columns = os.popen('stty size', 'r').read().split()
	usage         = 'python test_preclusters.py [options]\nA tool for empirically testing different combinations of pre-defined clusters.\nDefault values for options are in square brackets.'
	fmt           = optparse.IndentedHelpFormatter(max_help_position=int(columns) - 50, width=int(columns))
	parser        = optparse.OptionParser(usage=usage, formatter=fmt)
	
	parser.add_option('-s', '--source_dir',      help='Directory containing the individual cluster files. ["source_dir"]')
	parser.add_option('-o', '--output_dir',      help='Directory to which all combined files should be output. ["output_dir"]')
	parser.add_option('-e', '--output-file-ext', help='The file extension to use for all combined files. [None]')
	parser.add_option('-r', '--recursive',
	                  action = 'store_true',
	                  help   = 'Recursively traverse the specified directory.')
	parser.add_option('-R', '--regex',
	                  help = 'Only use files that match this regex (python re syntax) as clusters.')
	parser.add_option('-c', '--max-combinations',
	                  type = 'int',
	                  help = 'Test combinations of useful clusters with up to this many clusters combined together. 0 means no limit. Any value < 0 is meaningless and will be ignored. [0]')
	
	# set defaults and parse options, arguments
	parser.set_defaults(source_dir       = 'source_dir',
						output_dir       = 'output_dir',
						output_file_ext  = None,
						recursive        = None,
						regex            = None,
						max_combinations = 0)
	options, args = parser.parse_args()
	
	# clean up
	del fmt
	del parser
	del rows
	del columns
	
	# error check parameters
	if not isdir(options.source_dir):
		print 'Specified directory ( ' + options.source_dir + ' ) does not exist or is not a directory.'
		exit(1)
	if options.max_combinations < 0:
		options.max_combinations = 0
	
	# get list of cluster files according to given parameters
	files = listfiles(options.source_dir, recursive=options.recursive, regex=options.regex)
	
	# make sure there's files that match the given parameters
	if len(files) == 0:
		print 'No files match the given parameters.'
		exit(1)
	
	if options.max_combinations == 0:
		options.max_combinations = len(files)
	
	for length in range(1, options.max_combinations + 1):
		for combination in itertools.combinations(files, length):
			# get output file
			output_name = '_'.join(f[f.rfind('/') + 1:f.rfind('.') if f.rfind('.') != -1 else len(f)] for f in combination)
			if options.output_file_ext:
				output_name += '.' + options.output_file_ext
			outfile = open(join(options.output_dir, output_name), 'w')
			
			# write file contents to 
			for f in combination:
				f = open(f, 'r')
				outfile.write(f.read())
				f.close()


if __name__ == '__main__':
	main()
