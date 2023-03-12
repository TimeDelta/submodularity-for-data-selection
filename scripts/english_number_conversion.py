def textToNum(textnum, contains_only_numbers=False):
	units  = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
	          "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
	          "sixteen", "seventeen", "eighteen", "nineteen"]
	tens   = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
	scales = ["hundred", "thousand", "million", "billion", "trillion", "quadrillion", "quintillion",
	          "sextillion", "septillion", "octillion", "nonillion", "decillion", "undecillion",
	          "duodecillion", "tredecillion", "quattuordecillion", 'quindecillion', "sexdecillion",
	          "septendecillion", "octodecillion", "novemdecillion", "vigintillion"]
	numwords = dict()
	numwords["and"] = (1, 0)
	for idx, word in enumerate(units):  numwords[word] = (1, idx)
	for idx, word in enumerate(tens):   numwords[word] = (1, idx * 10)
	for idx, word in enumerate(scales): numwords[word] = (10 ** (idx * 3 or 2), 0)
	
	current        = result = 0
	new_text       = []
	number_started = None
	previous_word  = ''
	previous_added = None
	for word in textnum.split():
		original_word = word
		word          = word.lower()
		if word not in numwords or (not number_started and word == 'and') or (number_started and word == 'and' and previous_word.lower() == 'and'):
			if contains_only_numbers == True:
				raise Exception("Illegal word: " + original_word)
			else:
				if number_started:
					new_text.append(str(result + current))
					number_started = None
					current        = result = 0
				# for cases where the word 'and' comes immediately after a number
				if previous_word.lower() == 'and' and not previous_added:
					new_text.append(previous_word)
				new_text.append(original_word)
				previous_word  = original_word
				previous_added = True
				continue
		if not number_started:
			number_started = True
		
		# if previous_word.lower() == 'and' and word == 'and':
		# 	new_text.append(previous_word)
		
		scale, increment = numwords[word]
		current          = current * scale + increment
		if scale > 100:
			result += current
			current = 0
		previous_word  = original_word
		previous_added = None
	if len(new_text) == 0:
		if previous_word.lower() == 'and':
			new_text.append(str(result + current))
			new_text.append(previous_word)
		else:
			return result + current
	return ' '.join(new_text)


# properly handles string numbers (w/ or w/o commas) and integers
def numToText(num):
	import re
	units     = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
	teens     = ["", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
	             "eighteen", "nineteen"]
	tens      = ["", "ten", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
	thousands = ["","thousand", "million", "billion", "trillion", "quadrillion", "quintillion",
	             "sextillion", "septillion", "octillion", "nonillion", "decillion", "undecillion",
	             "duodecillion", "tredecillion", "quattuordecillion", 'quindecillion', "sexdecillion",
	             "septendecillion", "octodecillion", "novemdecillion", "vigintillion"]
    
    # make sure that num gets cast to a string
	if type(num) != str:
		num = str(num)
	
	# remove any commas between digits
	num = re.sub(r'(?<=[0-9]),(?=[0-9])', '', num)
	
	# remove any superfluous leading zeros
	decimal_index = num.find('.')
	if decimal_index > 0:
		start = num.find('-') + 1
		if decimal_index - start > 1:
			num = str(int(num[start:decimal_index])) + num[decimal_index:]
			if start == 1:
				num = '-' + num
	elif decimal_index == -1:
		start  = num.find('-') + 1
		num = str(int(num[start:]))
		if start == 1:
			num = '-' + num
	
	words = []
	if num[0] == '-':
		words.append('negative')
		num = num[1:]
	if re.match(r'0*\.?0+', num):
		words.append('zero')
	else:
		decimal_point_index = num.find('.')
		decimalStr          = None
		if decimal_point_index > -1:
			decimalStr = num[decimal_point_index + 1:]
			num     = num[:decimal_point_index]
		numLen = len(num)
		groups    = (numLen + 2) / 3
		num    = num.zfill(groups * 3)
		for i in range(0, groups*3, 3):
			h = int(num[i])
			t = int(num[i+1])
			u = int(num[i+2])
			g = groups - (i / 3 + 1)
			
			if h >= 1:
				words.append(units[h])
				words.append('hundred')
			
			if t > 1:
				words.append(tens[t])
				if u >= 1:
					words.append(units[u])
			elif t == 1:
				if u >= 1:
					words.append(teens[u])
				else:
					words.append(tens[t])
			else:
				if u >= 1:
					words.append(units[u])
			
			if g >= 1 and (h + t + u) > 0:
				words.append(thousands[g])
		if decimalStr:
			words.append('point')
			for i in range(0, len(decimalStr)):
				digit = int(decimalStr[i])
				if digit == 0:
					words.append('zero')
				else:
					words.append(units[digit])
	return ' '.join(words)


def num_replace(match):
	try:
		match = match.string[match.start():match.end()]
		return numToText(match).upper()
	except: # if the number is too large (> 66 digits)
		return ''


def main():
	import optparse
	
	usage  = 'python filter_sentences.py [options]\nA tool for converting between numbers written as words in English and digits.'
	fmt    = optparse.IndentedHelpFormatter(max_help_position=30, width=80)
	parser = optparse.OptionParser(usage=usage, formatter=fmt)
	
	# add options to the option parser
	parser.add_option('-t', '--text-to-num',
	                  action = 'store_true',
	                  help   = 'Convert the specified text to number. [Default converts from number to text]')
	parser.add_option('-f', '--file',
	                  default = None,
	                  help    = 'Convert the contents of a file instead.')
	parser.add_option('-o', '--output',
	                  default = None,
	                  help    = 'Write output to file instead of STDOUT.')
	parser.add_option('-n', '--only-numbers',
	                  action = 'store_true',
	                  help   = 'The specified text only contains english number words (with or without "and"). This throws an error if another word is encountered. (This is only applicable with the -t option)')
	
	# set defaults and parse options, arguments
	parser.set_defaults(text_to_num  = None,
	                    only_numbers = None)
	options, args = parser.parse_args()
	
	# clean up
	del fmt
	del parser
	
	# convert
	if options.file:
		import re
		num_re = re.compile(r'-?(((([1-9][0-9]*|0))?\.[0-9]*)|([1-9][0-9]*)|0)')
		with open(options.file, 'r') as f:
			result = ''
			for line in f:
				if options.text_to_num:
					text = str(textToNum(line, options.only_numbers))
				else:
					text = str(num_re.sub(num_replace, line))
				result += text + '\n'
	else:
		text = ' '.join(args)
		if options.text_to_num:
			result = str(textToNum(text, options.only_numbers))
		else:
			result = str(numToText(text))
	
	# output
	if options.output:
		with open(options.output, 'w') as f:
			f.write(result)
	else:
		print result


if __name__ == '__main__':
	main()
	
