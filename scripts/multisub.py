import re

###########
# WARNING #
################################################################################
# - Including overlapping regexes in the same MultiSub leads to UNDEFINED
#   BEHAVIOR
# - The use of numbered back references leads to UNDEFINED BEHAVIOR
#   - TODO: when compiling, search through each regex and keep a global back
#           reference count to correct numbered back references and avoid this
# - The definition of the same group name in more than one regex leads to
#   UNDEFINED BEHAVIOR
# - If the total number of groups in all of the regexes combined exceeds 100,
#   calling compile() will produce an ERROR. This is a built-in limit for the
#   python re module and cannot currently be changed.
################################################################################
class MultiSub(dict):
	def __init__(self, dic):
		self.re    = None
		self.regex = None
		dict.__init__(self, dic)
	
	
	def compile(self):
		if len(self) > 0:
			# or all of the regexes together
			temp_re = "%s" % "|".join(self.keys())
			
			# only recompile if there has been a change
			if self.re != temp_re:
				# store the regex string in case it is wanted later
				self.re = temp_re
				
				# compile the combined regex
				self.regex = re.compile(self.re)
				
				# compile all of the regex keys to decrease time complexity of sub()
				# using "in iteritems()" causes an infinite for loop that encounters
				# an error on its second time over the items in the dictionary
				for key, value in self.items():
					self.pop(key)
					self[re.compile(key + '$')] = value
	
	
	# making this a callable class enables easy mass substitution in sub()
	def __call__(self, match):
		# get the replacement value for the first regex that fully
		# matches the matched string
		matched_string = match.string[match.start():match.end()]
		for key, value in self.iteritems():
			if key.match(matched_string):
				# replacement = self[key]
				# replacement = re.sub(r'\\[1-9][0-9]*', lambda match2: match.group(match2.string[match2.start():match2.end()][1:])), replacement)
				# print replacement
				return re.sub(r'\\g<[^>]*>', lambda match2: match.group(match2.string[match2.start():match2.end()][3:-1]), self[key])
	
	
	# precondition:
	#     compile() has been called
	# replace in each occurences of one of the regexes in text
	# with its corresponding value
	def sub(self, text):
		if len(self) == 0:
			return text
		return self.regex.sub(self, text)
