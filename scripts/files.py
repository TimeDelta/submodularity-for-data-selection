from os.path import isfile, join
import re
from os import listdir


def splitDirs(option, opt, value, parser):
	setattr(parser.values, option.dest, value.split(','))


def listfiles(directories, recursive=None, regex=None):
	if type(directories) != list:
		directories = [directories]
	if type(regex) == str:
		regex = re.compile(regex)
	for directory in directories:
		if not recursive:
			if regex:# non-recursive, regex
				files = [ join(directory, f) for f in listdir(directory) if isfile(join(directory, f)) and regex.search(f) ]
			else:# non-recursive, no regex
				files = [ join(directory, f) for f in listdir(directory) if isfile(join(directory, f))]
		elif regex:# recursive, regex
			files = []
			for dir, subfolders, dir_files in os.walk(directory):
				files.extend( [ join(dir, file) for file in dir_files if regex.search(file) ] )
		else:# recursive, no regex
			files = []
			for dir, subFolders, dir_files in os.walk(directory):
				files.extend( [ join(dir, file) for file in dir_files ] )
	return files


# generator version (light weight when compared to other version)
def yieldfiles(directories, recursive=None, regex=None):
	if type(directories) != list:
		directories = [directories]
	if type(regex) == str:
		regex = re.compile(regex)
	for directory in directories:
		if not recursive:
			if regex:# non-recursive, regex
				for f in listdir(directory):
					if isfile(join(directory, f)) and regex.search(f):
						yield join(directory, f)
			else:# non-recursive, no regex
				for f in listdir(directory):
					if isfile(join(directory, f)):
						yield join(directory, f)
		elif regex:# recursive, regex
			for dir, subfolders, dir_files in os.walk(directory):
				for file in dir_files:
					if regex.search(file):
						yield join(dir, file)
		else:# recursive, no regex
			for dir, subFolders, dir_files in os.walk(directory):
				for file in dir_files:
					yield join(dir, file)


# this provides a non-python interface
def main():
	import optparse
	usage  = 'python files.py [options].'
	fmt    = optparse.IndentedHelpFormatter(max_help_position=30, width=80)
	parser = optparse.OptionParser(usage=usage, formatter=fmt)
	
	# add options to the option parser
	parser.add_option('-d', '--directories',
	                  type     = 'string',
	                  action   = 'callback',
	                  callback = splitDirs,
	                  help     = 'Comma separated list of directories in which to search. [.]')
	parser.add_option('-r', '--recursive',
	                  action   = 'store_true',
	                  help     = 'Recursively search all child directories.')
	parser.add_option('-R', '--regex',
	                  help     = 'Only consider files matching this (python) regex. This is mainly useful in cases where only certain file types are to be considered.')
	parser.add_option('-D', '--delimiter',
	                  help     = 'The delimiter to use for separating matched files in the output.')
	
	# set defaults and parse options, arguments
	parser.set_defaults(directories = ['.'],
	                    recursive   = None,
	                    regex       = None,
	                    delimiter   = ' : ')
	options, args = parser.parse_args()
	
	# clean up
	del fmt
	del parser
	
	print options.delimiter.join(listfiles(options.directories, options.recursive, options.regex))


if __name__ == '__main__':
	main()
