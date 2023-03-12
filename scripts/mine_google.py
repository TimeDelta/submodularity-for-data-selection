# coding=utf-8
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# ! IMPORTANT ! Do NOT remove the first line of this file, you will break the code !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
import os, sys, re, optparse, random, operator, unicodedata, time
from math import log10, sqrt
# from pprint import pprint

from pattern.web import URL, URLError, plaintext

from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice, TagExtractor
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.cmapdb import CMapDB
from pdfminer.layout import LAParams
from pdfminer.image import ImageWriter

try:
	# Try importing for Python 3
	# pylint: disable-msg=F0401
	# pylint: disable-msg=E0611
	from urllib.request import HTTPCookieProcessor, Request, build_opener
	from urllib.parse import quote
	from http.cookiejar import CookieJar
except ImportError:
	# Fallback for Python 2
	from urllib2 import Request, build_opener, HTTPCookieProcessor
	from urllib import quote
	from cookielib import CookieJar

# Import BeautifulSoup -- try 4 first, then fall back to older
try:
	from bs4 import BeautifulSoup
except ImportError:
	try:
		from BeautifulSoup import BeautifulSoup
	except:
		print('Must first install BeautifulSoup ... Sorry!')
		sys.exit(1)

# Support unicode in both Python 2 and 3. In Python 3, unicode is str.
if sys.version_info[0] == 3:
	unicode = str # pylint: disable-msg=W0622
	encode = lambda s: s # pylint: disable-msg=C0103
else:
	encode = lambda s: s.encode('utf-8') # pylint: disable-msg=C0103

#################################################################################################

'''""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
This class will query Google's search engine and return the resulting
HTML page.
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
class GoogleQuerier(object):
	GOOGLE_URL = 'https://www.google.com/search?client=safari&rls=en&q=%(query)s&ie=UTF-8&oe=UTF-8&num=%(count)s'
	USER_AGENT = 'Mozilla/5.0 (X11; U; FreeBSD i386; en-US; rv:1.9.2.9) Gecko/20100913 Firefox/3.6.9'
	
	def __init__(self, count=10):
		# Google doesn't support more than 100 results per page
		self.count  = min(count, 100)
		self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
	
	def query(self, query):
		url     = self.GOOGLE_URL % {'query': quote(encode(query)), 'count': str(self.count)}
		timeout = 3# number of tries before erroring out
		while timeout > 0:
			try:
				return self.opener.open(Request(url=url, headers={'User-Agent': self.USER_AGENT})).read()
			except KeyboardInterrupt:
				raise
			except:
				timeout -= 1
				if timeout > 0:
					time.sleep(5)
		return None

#################################################################################################

class Result(object):
	def __init__(self):
		self.url       = ''
		self.title     = ''
		self.summary   = ''
		self.full_text = ''

#################################################################################################

'''""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
This class will parse the HTML of a page returned by Google's search
engine.
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
class GoogleParser(object):
	def __init__(self, quiet, verbose, forbidden_phrases):
		self.soup                  = None
		self.quiet                 = quiet
		self.verbose               = verbose
		self.forbidden_url_phrases = forbidden_phrases
		self.visited_urls          = []
	
	
	def parse_results_page(self, html):
		results = []
		if html:
			self.soup = BeautifulSoup(html)
			i = 1
			for result in self.soup.findAll(GoogleParser.is_result):
				parsed_result = self.parse_result(result, i)
				if parsed_result == -1:
					i -= 1
				elif parsed_result:
					results.append(parsed_result)
					self.visited_urls.append(parsed_result.url)
				i += 1
			if not self.quiet:
				print '    Total Results Parsed:\t' + str(len(results))
		elif not self.quiet:
			print '    COULD NOT COMPLETE REQUEST'
		return results
	
	
	# return value of -1 means the tag was not a webpage result (usually a collection of images that Google adds)
	# return value of None means that the associated URL either contained a forbidden word or has already been mined
	def parse_result(self, outer_tag, i):
		result       = Result()
		result.title = ''.join(outer_tag.h3.a.findAll(text=True))
		result.url   = outer_tag.h3.a['href']
		if result.url in self.visited_urls:
			if not self.quiet and self.verbose:
				print '    ' + str(i) + ')' + ' '*(4 - len(str(i))) + 'REPEAT:\t' + result.url
			return None
		if result.url.startswith('/url?q='):
			index      = result.url.find('&sa=')
			result.url = result.url[7:index]
			for phrase in self.forbidden_url_phrases:
				if result.url.lower().find(phrase.lower()) > -1:
					if not self.quiet and self.verbose:
						print '    ' + str(i) + ')' + ' '*(4 - len(str(i))) + 'UNWANTED:\t' + result.url
					return None
			try:
				URL(result.url).open()
			except:
				index = result.url.find('%')
				if index > -1:
					result.url = result.url[:index]
				try:
					URL(result.url).open()
				except:
					if not self.quiet and self.verbose:
						print '    ' + str(i) + ')' + ' '*(4- len(str(i))) + 'UNABLE TO REACH:\t' + result.url
					return None
		else:
			# tag does not represent a proper result
			return -1
		# result.summary = ''.join(outer_tag.div.span.findAll(text=True))
		url    = result.url
		result = self.parse_full_text(result)
		if not self.quiet and self.verbose:
			if not result:
				print '    ' + str(i) + ')' + ' '*(4 - len(str(i))) + 'UNABLE TO DOWNLOAD:\t' + url
			else:
				print '    ' + str(i) + ')' + ' '*(4 - len(str(i))) + result.title + '\n           ' + url
		return result
	
	
	@staticmethod
	def parse_full_text(result):
		try:
			if result.url.endswith('.pdf'):
				result = GoogleParser.parsePDF(result)
			elif not result.url.endswith('.ppt'):
				result.full_text = unicodedata.normalize('NFKD', plaintext(URL(result.url).open().read())).encode('ascii', 'ignore')
		except:
			return None
		
		return result
	
	
	@staticmethod
	def parsePDF(result):
		f = open('/tmp/temp.pdf', 'w')
		f.write(URL(result.url).download())
		f.close()
		
		f = open('/tmp/temp.pdf', 'rb')
		
		rsrcmgr = PDFResourceManager(caching=True)
		outfp   = file('/tmp/temp-pdf.txt', 'w')
		device  = TextConverter(rsrcmgr, outfp, codec='utf-8', laparams=LAParams(), imagewriter=None)
		
		# parse the PDF document
		interpreter = PDFPageInterpreter(rsrcmgr, device)
		for page in PDFPage.get_pages(f, set(), maxpages=0, password='', caching=True, check_extractable=True):
			interpreter.process_page(page)
		f.close()
		device.close()
		outfp.close()
		
		# read in the resulting text
		f = open('/tmp/temp-pdf.txt', 'r')
		result.full_text = f.read()
		f.close()
		
		# remove the temporary files
		os.system('rm -f /tmp/temp.pdf /tmp/temp-pdf.txt')
		
		return result
	
	
	@staticmethod
	def tag_has_class(tag, klass):
		"""
		This predicate function checks whether a BeatifulSoup Tag instance
		has a class attribute.
		"""
		res = tag.get('class') or []
		if type(res) != list:
			# BeautifulSoup 3 can return e.g. 'gs_md_wp gs_ttss',
			# so split -- conveniently produces a list in any case
			res = res.split()
		return klass in res
	
	
	@staticmethod
	def is_result(tag):
		return tag.name == 'li' and GoogleParser.tag_has_class(tag, 'g')

#################################################################################################

'''""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Randomly pick a key in the specified dictionary based on the weight
of each key's value.
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
def weightedRandom(dictionary, total_weight):
	# scramble the internal state of the random number generator
	random.jumpahead(random.randint(0, 9999999999))
	
	rand  = random.uniform(0, total_weight)
	sum   = 0.0
	items = dictionary.items()
	
	# shuffle the items to avoid an unfair advantage to the keys that
	# appear earlier in the dictionary
	random.shuffle(items)
	
	for key, weight in items:
		sum += weight
		if rand < sum:
			return key
	return key

#################################################################################################

'''""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Generates a (n word tuple: count) dictionary from a list of text
files. Text files must be only alphabetic characters and white space.
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
def getCounts(seed_file, n):
	ngrams = {}
	
	f = open(seed_file, 'r')
	for line in f:
		line = line.rstrip()
		wordList = line.split()
		
		for i in range(len(wordList) - n + 1):
			gram = tuple(wordList[i:i+n])
			
			if gram in ngrams:
				ngrams[gram] += 1
			else:
				ngrams[gram] = 1
	f.close()
	
	return ngrams

#################################################################################################

'''"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
Return the total count of all n-grams.
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
def getTotalCount(dictionary):
	sortedDict = sorted(dictionary.iteritems(), key=operator.itemgetter(1), reverse=True)
	count = 0
	
	for entry in sortedDict:
		count += entry[1]
	
	return count

#################################################################################################

def getDictCtSafe(dict, entry):
	if entry in dict:
		return dict[entry]
	else :
		return 0

#################################################################################################

'''"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
t_one:
  measures the decrease in probability mass resulting from adding more
  words
t_two:
  measures the seed weighted improvement in probability for words in
  the current sentence
if t_one < t_two the relative entropy is decreased (keep the sentence)

See "Selecting relevant text subsets from web-data for building topic
specific language models" for further reference. This algorithm is
roughly based on one described in that research paper, but is expanded
to filter on trigram counts rather than unigram counts.
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""'''
def incrementalFilter(seed_file, previously_mined, mined_text, quiet):
	p = getCounts(seed_file, 3)
	w = getCounts(seed_file, 3)
	n = getTotalCount(w)
	
	output = ''
	
	# add the seed sentences
	f     = open(seed_file, 'r')
	lines = f.read().splitlines()
	f.close()
	
	# add the previously mined sentences
	if previously_mined:
		f = open(previously_mined, 'r')
		lines.extend(f.read().splitlines())
		f.close()
	
	# add the mined sentences
	lines.extend(mined_text.splitlines())
	
	# delete duplicates, then shuffle
	lines = list(set(lines))
	random.seed()
	random.shuffle(lines)
	
	size = 0
	
	# i is an arbitrary scalar added to t_one as 1/i.
	# this makes filtering more strict with larger i values.
	for i in range(11,13):
		if not quiet:
			print '  Iteration ' + str(i - 10)
		removeList = []
		
		for line in lines:
			removeList.append(line)
			line = line.strip()
			wordList = line.split()
			linegrams = {}
			
			# populate linegrams with the current line
			for j in range(len(wordList) - 3 + 1):
				gram = tuple(wordList[j:j+3])
				
				if gram in linegrams:
					linegrams[gram] += 1
				else:
					linegrams[gram] = 1
			
			# the last term of t_one is an arbitrary scalar to make the
			# filtering more strict. it can be anything.
			t_one = log10(float(n + len(wordList))/float(n)) + 1.0/float(i)
			t_two = 0.0
			
			for gram in linegrams:
				if gram in w:
					t_two = t_two + log10(float(w[gram] + linegrams[gram])/float(w[gram])) * float(getDictCtSafe(p,gram))
				#TODO: revisit this. it doesn't work as is, but I would like to add extra weight on oov.
				#else:
				#	#place extra weight on introducing new words to vocab
				#	t_two = t_two + 50.0
			
			if t_one < t_two:
				for gram in linegrams:
					if gram in w:
						w[gram] += 1
					else:
						w[gram] = 1
				
				output += line + '\n'
				size = size + len(line)
			else:
				removeList.pop()
		# if not quiet:
		# 	print '  ' + str(len(removeList)) + " sentences added"
		# 	print '  ' + str(len(lines)) + " sentences before filter"
		# remove all lines that have been added to output file
		# lines = filter (lambda a: removeList.count(a) == 0, lines)
		# if not quiet:
		# 	print '  ' + str(len(lines)) + " sentences after filter"
	return output

#################################################################################################

def nonincrementalFilter(seed_file, previously_mined, mined_text, quiet):
	p = getCounts(seed_file, 3)
	w = getCounts(seed_file, 3)
	n = getTotalCount(w)
	
	output = ''
	
	# add the seed sentences
	f     = open(seed_file, 'r')
	lines = f.read().splitlines()
	f.close()
	
	# add the previously mined sentences
	if previously_mined:
		f = open(previously_mined, 'r')
		lines.extend(f.read().splitlines())
		f.close()
	
	# add the mined sentences
	lines.extend(mined_text.splitlines())
	
	# delete duplicates, then shuffle
	lines = list(set(lines))
	random.seed()
	random.shuffle(lines)

	for line in lines:
		line = line.strip()
		wordList = line.split()
		linegrams = {}
		
		for i in range(len(wordList) - 3 + 1):
			gram = tuple(wordList[i:i+3])
			
			if gram in linegrams:
				linegrams[gram] += 1
			else:
				linegrams[gram] = 1
		
		t_one = log10(float(n + len(wordList))/float(n))
		t_two = 0.0
		
		for gram in linegrams:
			if gram in w:
				t_two = t_two + log(float(w[gram] + linegrams[gram])/float(w[gram])) * float(p[gram])
			#TODO: revisit this.  it doesn't work as is, but I would like to add extra weight on oov.
			#else:
			#	#place extra weight on introducing new words to vocab
			#	t_two = t_two + 50.0
		
		if t_one < t_two:
			output += line + '\n'
	return output

#################################################################################################

units = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE "]
teens = ["", "ELEVEN", "TWELVE", "THIRTEEN", "FOURTEEN", "FIFTEEN", "SIXTEEN", "SEVENTEEN",
	"EIGHTEEN", "NINETEEN"]
tens = ["", "TEN", "TWENTY", "THIRTY", "FORTY", "FIFTY", "SIXTY", "SEVENTY", "EIGHTY", "NINETY"]
thousands = ["","THOUSAND", "MILLION", "BILLION", "TRILLION", "QUADRILLION", "QUINTILLION",
	"SEXTILLION", "SEPTILLION", "OCTILLION", "NONILLION", "DECILLION", "UNDECILLION",
	"DUODECILLION", "TREDECILLION", "QUATTUORDECILLION", "SEXDECILLION", "SEPTENDECILLION",
	"OCTODECILLION", "NOVEMDECILLION", "VIGINTILLION "]

def numToWordString(numStr):
	# remove any superfluous leading zeros
	decimal_index = numStr.find('.')
	if decimal_index > 0:
		start = numStr.find('-') + 1
		if decimal_index - start > 1:
			numStr = str(int(numStr[start:decimal_index])) + numStr[decimal_index:]
			if start == 1:
				numStr = '-' + numStr
	elif decimal_index == -1:
		start = numStr.find('-') + 1
		numStr = str(int(numStr[start:]))
		if start == 1:
			numStr = '-' + numStr
	
	words = []
	if numStr[0] == '-':
		words.append('NEGATIVE')
		numStr = numStr[1:]
	if numStr == '0' or numStr == '0.0':
		words.append("ZERO")
	else:
		decimal_point_index = numStr.find('.')
		decimalStr = None
		if decimal_point_index > -1:
			decimalStr = numStr[decimal_point_index + 1:]
			numStr     = numStr[:decimal_point_index]
		numStrLen = len(numStr)
		groups    = (numStrLen + 2) / 3
		numStr    = numStr.zfill(groups * 3)
		for i in range(0, groups*3, 3):
			h = int(numStr[i])
			t = int(numStr[i+1])
			u = int(numStr[i+2])
			g = groups - (i / 3 + 1)
			
			if h >= 1:
				words.append(units[h])
				words.append("HUNDRED")
			
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
				try:
					words.append(thousands[g])
				except:
					print 'ERROR:\twords.append(thousands[' + str(g) + '])\t'
					print words
					print numStr
		if decimalStr:
			words.append('POINT')
			for i in range(0, len(decimalStr)):
				digit = int(decimalStr[i])
				if digit == 0:
					words.append('ZERO')
				else:
					words.append(units[digit])
	return ' '.join(words)

#################################################################################################

months = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER',
	'OCTOBER', 'NOVEMBER', 'DECEMBER']
days   = ['FIRST', 'SECOND', 'THIRD', 'FOURTH', 'FIFTH', 'SIXTH', 'SEVENTH', 'EIGHTH', 'NINETH',
	'TENTH', 'ELEVENTH', 'TWELFTH', 'THIRTEENTH', 'FOURTEENTH', 'FIFTEENTH', 'SIXTEENTH',
	'SEVENTEENTH', 'EIGHTEENTH', 'NINETEENTH', 'TWENTIETH', 'TWENTY FIRST', 'TWENTY SECOND',
	'TWENTY THIRD', 'TWENTY FOURTH', 'TWENTY FIFTH', 'TWENTY SIXTH', 'TWENTY SEVENTH',
	'TWENTY EIGTH', 'TWENTY NINTH', 'THIRTIETH', 'THIRTY FIRST']

# currently, this method returns the empty string if the date string does not follow MONTH DAY YEAR ordering
def replaceDate(date):
	replacement = ''
	index       = date.find('-')
	separator   = '/'
	if index < 0:
		index = date.find('/')
		if index < 0:
			index     = date.find('\\')
			separator = '\\'
		else:
			separator = '/'
	
	# month
	number = int(date[:index])
	if number < 1:
		return ''
	if number > 12:
		return ''
	replacement = months[number - 1] + ' '
	
	# day
	rindex = date.rfind(separator)
	if rindex <= index:
		return ''
	number = int(date[index + 1:rindex])
	if number < 1:
		return ''
	if number > 31:
		return ''
	replacement += days[number - 1] + ' '
	
	#year
	index  = date.rfind(separator) + 1
	number = date[index:]
	if len(number) == 2:
		if number[0] == '0':
			if number[1] == '0':
				replacement += 'TWO THOUSAND'
			else:
				replacement += 'O '
				replacement += units[int(number[1])]
		else:
			replacement += numToWordString(number)
	else:
		replacement += numToWordString(number[:2])
		replacement += numToWordString(number[2:])
	return replacement

#################################################################################################

def replaceTime(time):
	midnight_re = re.compile(r'((12)|(00)):00( ?(AM)|(A))')
	if midnight_re.match(time):
		return 'TWENTY FOUR HUNDRED'
	
	replacement = ''
	colon_index = time.find(':')
	
	hours = time[:colon_index]
	if time.find('P') > -1:
		hours = str(int(hours) + 12)
	time = hours + time[colon_index:]
	colon_index = time.find(':')
	
	# hours
	version = None
	if colon_index == 1 or time[0] == '0':
		version = random.randint(0,100) % 2
		if version == 0:
			replacement += 'O '
		else:
			replacement += 'ZERO '
		if time[0] != '0':
			replacement += units[int(time[0])] + ' '
		if time[1] == '0':
			if version == 0:
				replacement += 'O '
			else:
				replacement += 'ZERO '
		elif time[1] != ':':
			replacement += units[int(time[1])] + ' '
	else:
		replacement += numToWordString(hours) + ' '
	
	# minutes
	time = re.sub(r'[A-Z ]', '', time)
	if time[colon_index + 1:] == '00':
		return replacement + 'HUNDRED'
	elif time[colon_index + 1] == '0':
		if not version:
			version = random.randint(0,100) % 2
		if version == 0:
			replacement += 'O '
		else:
			replacement += 'ZERO '
		colon_index += 1
	return replacement + numToWordString(str(int(time[colon_index + 1:])))

#################################################################################################

def main():
	rows, columns = os.popen('stty size', 'r').read().split()
	
	usage  = """python mineGoogle.py [options]
A tool for getting additional data relevant to a topic as
represented in an ARPA file and a set of seed sentences."""
	
	fmt    = optparse.IndentedHelpFormatter(max_help_position=int(columns) - 50, width=int(columns))
	parser = optparse.OptionParser(usage=usage, formatter=fmt)
	
	# add options to the option parser
	parser.add_option('-i', '--input',                               help='ARPA file to use. This helps determine the weighted random trigram search queries. ["input.arpa"]')
	parser.add_option('-s', '--seed',                                help='File containing seed sentences to use. ["seedsentences"]')
	parser.add_option('-o', '--original',                            help='Append the downloaded text (pre-processed) to the end of the specified file.')
	parser.add_option('-c', '--cleaned',                             help='Append the downloaded text (post-cleaning , pre-filtering) to the end of the specified file.')
	parser.add_option('-a', '--append',                              help='Append the useful sentences to the end of the specified file. If not specified, console will be used.')
	parser.add_option('-U', '--store-urls',                          help='Store the URLs visited in this file. [WARNING] This will overwrite the contents of the specified file.')
	parser.add_option('-f', '--forbidden-urls',                      help='File containing phrases that cannot appear in an acceptable URL.')
	parser.add_option('-C', '--common',                              help='File containing a list of common words to help filter search queries. If a query contains only words from this list, it will be ignored.')
	parser.add_option('-p', '--prev-mined',     action='store_true', help='Inclued the previously mined sentences in the entropy calculations.')
	parser.add_option('-e', '--experimental',   type='int',          help='Use the unigram probabilities to further weed out bad search queries. The integer is the minimum number of std deviations away from the highest probability.')
	parser.add_option('-n', '--nonincremental', action='store_true', help='Use non-incremental filtering algorithm for filtering out junk sentences. Default is incremental.')
	parser.add_option('-r', '--results',        type='int',          help='The number of results to use per query. [15]')
	parser.add_option('-Q', '--queries',        type='int',          help='The number of queries to run. [100]')
	parser.add_option('-A', '--all-queries',    action='store_true', help='Run every trigram query that passes query filtering. This option precludes the option "-Q"')
	parser.add_option('-t', '--trigrams',                            help='Write all of the trigram search queries that remain after query filtering to the specified file along with their probabilities.')
	parser.add_option('-S', '--search-file',                         help='File containing additional search queries to perform.')
	parser.add_option('-F', '--search-file-only',                    help='File containing search queries to perform. This option precludes any combination of options: -i -C -e -Q -S -u -A')
	parser.add_option('-u', '--urls',                                help='File containing a list of additional URLs to mine.')
	parser.add_option('-O', '--urls-only',                           help='File containing a list of URLs to mine. This option precludes any combination of options: -i -C -e -r -Q -S -u -U -F -f -A')
	parser.add_option('-q', '--quiet',          action='store_true', help='Quiet mode. Precludes -v option.')
	parser.add_option('-v', '--verbose',        action='store_true', help='Verbose mode.')
	
	parser.set_defaults(input='input.arpa',
						seed='seedsentences',
						original=None,
						cleaned=None,
						append=None,
						store_urls=None,
						forbidden_urls=None,
						common=None,
						prev_mined=None,
						experimental=None,
						nonincremental=None,
						results=15,
						queries=100,
						trigrams=None,
						all_queries=None,
						search_file=None,
						search_file_only=None,
						urls=None,
						urls_only=None,
						quiet=None,
						verbose=None)
	options, args = parser.parse_args()
	
	# clean up
	del fmt
	del parser
	del rows
	del columns
	
	if not options.search_file_only and not options.urls_only:
		# read forbidden URL phrases
		forbidden_url_phrases = []
		if options.forbidden_urls:
			if not options.quiet:
				print 'Reading forbidden URL phrases'
			infile = open(options.forbidden_urls, 'r')
			for line in infile:
				forbidden_url_phrases.append(line.strip())
		
		if options.common:
			common_words = []
			if not options.quiet:
				print 'Reading common words file'
			infile = open(options.common, 'r')
			for line in infile:
				common_words.append(line.strip())
		
		# read in the ARPA file
		dictionary = dict()
		unigrams   = dict()
		if not options.quiet:
			print 'Reading ARPA file'
		infile = open(options.input, 'r')
		for line in infile:
			if line.startswith('\\1'):
				break
		if options.experimental or options.common:
			for line in infile:
				entry = line.strip().split()
				if len(entry) == 0:
					break
				unigrams[entry[1]] = pow(10, float(entry[0]))
		# experimental - if all 3 words in a trigram entry are less than
		# 1.5 standard deviations away from the highest probability
		if options.experimental:
			if not options.quiet:
				print 'Performing experimental unigram removal'
			
			# calculate the standard deviation of the unigram probabilities
			mean = 0
			for entry in unigrams:
				mean += unigrams[entry]
			mean   /= len(unigrams)
			std_dev = 0
			for entry in unigrams:
				std_dev += pow(unigrams[entry] - mean, 2)
			std_dev = sqrt(std_dev / len(unigrams))
			
			# get the highest probability in the unigrams
			sorted_probs = sorted(unigrams.iteritems(), key=operator.itemgetter(1))
			high         = sorted_probs[len(sorted_probs) - 1][1]
			
			# talk to the user
			if not options.quiet and options.verbose:
				print '  MEAN UNIGRAM PROBABILITY:              \t' + str(mean)
				print '  STANDARD DEVIATION UNIGRAM PROBABILITY:\t' + str(std_dev)
				print '  HIGHEST UNIGRAM PROBABILITY:           \t' + str(high)
			
			# remove all unigrams that are less than 1.5 standard deviations
			# away from the highest probability unigram
			grams = unigrams.keys()
			for entry in grams:
				if high - unigrams[entry] < options.experimental * std_dev:
					# if not options.quiet:
					# 	print '  - IGNORING UNIGRAM:\t' + entry + ' '*(20-len(entry)) + str(unigrams.pop(entry))
					# else:
					unigrams.pop(entry)
			# clean up
			del high
			del std_dev
			del mean
			del sorted_probs
		if options.common:
			if not options.quiet:
				print 'Performing common word removal'
			for word in common_words:
				if word in unigrams:
					if not options.quiet and options.verbose:
						print '  IGNORING WORD:\t' + word + ' '*(50-len(word)) + str(unigrams.pop(word))
					else:
						unigrams.pop(word)
			del common_words
		for line in infile:
			if line.startswith('\\3'):
				break
		if not options.quiet:
			print 'Reading in valid trigram search queries'
			trigrams_ignored = 0
			total_trigrams   = 1
		for line in infile:
			if line.startswith('-'):
				entry = line.strip().split()
				if entry[1] != '<s>':# can't represent beginning of sentence in a search
					if options.experimental or options.common:
						if entry[1] in unigrams or entry[2] in unigrams or entry[3] in unigrams:
							dictionary[tuple(entry[1:4])] = pow(10, float(entry[0]))
						elif not options.quiet:
							trigrams_ignored += 1
						# 	print '  - IGNORING TRIGRAM:\t' + str(entry[1:4]) + ' '*(35-len(str(entry[1:4]))) + str(pow(10, float(entry[0])))
					else:
						dictionary[tuple(entry[1:4])] = pow(10, float(entry[0]))
					total_trigrams += 1
		infile.close()
		if not options.quiet and options.verbose:
			print '    Total Queries Before Filtering: ' + str(total_trigrams)
			print '  - Total Queries Filtered:         ' + str(trigrams_ignored)
			print '  ----------------------------------' + '-' * len(str(total_trigrams))
			print '    Total Queries After Filtering:  ' + str(len(dictionary))
			
			# clean up
			del total_trigrams
			del trigrams_ignored
		del infile
		del unigrams
		
		# change the probability distribution so that words that are in the middle
		# are more likely to be picked for querying. the idea is that high-probability
		# trigrams are just commonly occurring to every subject and low-probability
		# ones are not very representative of the topic.
		# use the median as the middle to be more robust against outliers
		if not options.quiet:
			print 'Calculating query probabilities'
		sorted_probs = sorted(dictionary.iteritems(), key=operator.itemgetter(1))
		median_prob  = sorted_probs[int(len(sorted_probs)/2)][1]
		for key, value in dictionary.iteritems():
			if median_prob - value == 0:
				dictionary[key] = -1
			else:
				dictionary[key] = 1 / abs(median_prob - value)
		# get the highest value after the median
		sorted_probs = sorted(dictionary.iteritems(), key=operator.itemgetter(1))
		next_highest = sorted_probs[len(sorted_probs) - 1][1]
		# estimate the approximate value for the median
		estimated_value = 1.5 * next_highest# arbitrary scalar chosen
		# set the keys with median value to the estimated value
		for key, value in dictionary.iteritems():
			if value == -1:
				dictionary[key] = estimated_value # .05 * estimated_value
			# dictionary[key] = .95 * estimated_value - dictionary[key]
		
		# TODO: look into further modifying probability distribution
		#       based on trigrams with the highest amount of entropy
		
		if options.trigrams:
			if not options.quiet:
				print 'Writing remaining trigrams to file'
			trigrams_file   = open(options.trigrams, 'w')
			sorted_trigrams = sorted(dictionary.iteritems(), key=operator.itemgetter(1))
			for trigram in sorted_trigrams:
				trigrams_file.write(str(trigram[0]) + ' '*(50-len(str(trigram[0]))) + str(trigram[1]) + '\n')
			trigrams_file.close()
			del trigrams_file
		
		random.seed()
		
		# add up all the weights in the dictionary
		total_weight = 0.0
		for key, value in dictionary.iteritems():
			total_weight += value
		
		# make sure that all queries are ran if the user wants
		if options.all_queries:
			options.queries = len(dictionary)
		
		# run the queries
		if not options.quiet:
			print 'Running queries'
		results = []
		querier = GoogleQuerier(options.results)
		parser  = GoogleParser(options.quiet, options.verbose, forbidden_url_phrases)
		for i in range(0, options.queries):
			# select the next query, replacing any ending "</s>" token with a period
			entry = weightedRandom(dictionary, total_weight)
			dictionary.pop(tuple(entry))# avoid using the same query twice
			q     = '"' + re.sub(r'((\bU S\b)|((?<!\')\bS))\b', 'U.S.',  ' '.join(entry).replace(' </s>', '.')) + '"'
			q     = re.sub(r'\bO TWO\b',   'O2',   q)
			q     = re.sub(r'\bSPO TWO\b', 'SPO2', q)
			if not options.quiet:
				print '  Performing Query ' + str(i + 1) + ':\t' + q
			
			# perform the next query
			results.extend(parser.parse_results_page(querier.query(q)))
			
			if len(dictionary) == 0:
				print '  Ran out of trigram queries'
				break
		del dictionary
	
	# perform custom queries
	if options.search_file:
		if not options.quiet:
			print 'Running additional queries'
		search_file = open(options.search_file, 'r')
	elif options.search_file_only:
		results = []
		querier = GoogleQuerier(options.results)
		parser  = GoogleParser(options.quiet, options.verbose, [])
		if not options.quiet:
			print 'Running custom queries'
		search_file = open(options.search_file_only, 'r')
	i = 1
	if options.search_file or options.search_file_only:
		for line in search_file:
			line = '"' + line.strip() + '"'
			if not options.quiet:
				print '  Performing Query ' + str(i) + ':\t' + line
			
			# perform the next query
			results.extend(parser.parse_results_page(querier.query(line)))
			
			i += 1
		search_file.close()
		del search_file
	
	# output the urls visited if user requested to do so
	if options.store_urls:
		if not options.quiet:
			print 'Writing visited urls to file'
		out = open(options.store_urls, 'w')
		for url in parser.visited_urls:
			out.write(url + '\n')
		out.close()
		del out
	
	# parse specified urls
	if options.urls_only:
		results = []
		querier = GoogleQuerier(options.results)
		parser  = GoogleParser(options.quiet, forbidden_url_phrases)
		if not options.quiet:
			print 'Parsing urls'
		urls_file = open(options.urls_only, 'r')
	elif options.urls:
		if not options.quiet:
			print 'Parsing additional urls'
		urls_file = open(options.urls, 'r')
	if options.urls_only or options.urls:
		for line in urls_file:
			if not options.quiet:
				if result.url in parser.visited_urls:
					print '  SKIPPING REPEAT URL:\t' + line
				else:
					print '  Parsing ' + line
			result     = Result()
			result.url = line
			result     = GoogleParser.parse_full_text(result)
			if result:
				results.append(result)
		del result
		urls_file.close()
		del urls_file
	del parser
	del querier
	
	# concatenate all of the mined text
	print 'Concatenating mined text'
	mined_text = ''
	for result in results:
		mined_text += result.full_text + '.'
	
	# clean up
	del results
	
	# append the pre-processed text to the specified file
	if options.original:
		if not options.quiet:
			print 'Appending pre-processed text to requested file'
		original_file = open(options.original, 'a')
		original_file.write(mined_text)
		original_file.close()
		del original_file
	
	# replace unicode hyphens with ASCII hyphen
	mined_text = re.sub(r'–|—|−', '-', mined_text)
	
	# capitalize everything
	if not options.quiet:
		print 'Cleaning up mined text'
		print '  Capitalizing text'
	mined_text = mined_text.upper()
	
	# remove newlines
	mined_text = re.sub(r'\n', ' ', mined_text)
	mined_text = re.sub(r'\r', ' ', mined_text)
	
	# remove wikipedia references
	mined_text = re.sub(r'\[[0-9]+\]', '', mined_text)
	mined_text = re.sub(r'\[EDIT\]',   '', mined_text)
	
	# make each interjection a new sentence w/o splitting the rest of the sentence
	# if not options.quiet:
	# 	print '  Separating interjections'
	# interjection_re = re.compile(r',[^,\.;\?!…\n]+[,\.;\?!…]')
	
	# replace time of day references
	if not options.quiet:
		print '  Replacing time of day references'
	time_re = re.compile(r'(?<=\s)[0-2]?[0-9]:[0-5][0-9](\s*((AM)|(PM)|(A)|(P)|(M))\b)?')
	start   = 0
	match   = time_re.search(mined_text)
	next    = mined_text
	while match:
		replacement = replaceTime(next[match.start():match.end()])
		mined_text  = mined_text[:start + match.start()] + replacement + mined_text[start + match.end():]
		start       += match.start() + len(replacement)
		next        = next[match.end():]
		match       = time_re.search(next)
	del time_re
	
	# add a space in between numbers and letters
	if not options.quiet:
		print '  Inserting spaces between letters and numbers'
	mined_text = re.sub(r'((?<=[0-9])(?=[A-Z]))|((?<=[A-Z])(?=[0-9]))', ' ', mined_text)
	
	# replace dates
	if not options.quiet:
		print '  Replacing dates (i.e. 4-16-04, etc.)'
	mined_text = re.sub(r'\bJAN(\.|\b)',  'JANUARY',         mined_text)
	mined_text = re.sub(r'\bFEB(\.|\b)',  'FEBRUARY',        mined_text)
	mined_text = re.sub(r'\bMAR(\.|\b)',  'MARCH',           mined_text)
	mined_text = re.sub(r'\bAPR(\.|\b)',  'APRIL',           mined_text)
	mined_text = re.sub(r'\bJUN(\.|\b)',  'JUNE',            mined_text)
	mined_text = re.sub(r'\bJUL(\.|\b)',  'JULY',            mined_text)
	mined_text = re.sub(r'\bAUG(\.|\b)',  'AUGUST',          mined_text)
	mined_text = re.sub(r'\bSEP(\.|\b)',  'SEPTEMBER',       mined_text)
	mined_text = re.sub(r'\bSEPT(\.|\b)', 'SEPTEMBER',       mined_text)
	mined_text = re.sub(r'\bOCT(\.|\b)',  'OCTOBER',         mined_text)
	mined_text = re.sub(r'\bNOV(\.|\b)',  'NOVEMBER',        mined_text)
	mined_text = re.sub(r'\bDEC(\.|\b)',  'DECEMBER',        mined_text)
	date_re = re.compile(r'[0-9]{1,2}(-|/|\\)[0-9]{1,2}\1[0-9]{2}([0-9]{2})?')
	match   = date_re.search(mined_text)
	start   = 0
	next    = mined_text
	while match:
		replacement = replaceDate(next[match.start():match.end()])
		mined_text = mined_text[:start + match.start()] + replacement + mined_text[start + match.end():]
		start      += len(replacement) + match.start()
		next       = next[match.end():]
		match      = date_re.search(next)
	
	# replace numbers that follow months
	date_re = re.compile(r'\b(?:(JANUARY)|(FEBRUARY)|(MARCH)|(APRIL)|(MAY)|(JUNE)|(JULY)|(AUGUST)|(SEPTEMBER)|(OCTOBER)|(NOVEMBER)|(DECEMBER)) (([0-2][0-9])|(3[01])|([0-9]))( ?(TH)|(ST)|(ND)|(RD))?\b')
	match   = date_re.search(mined_text)
	start   = 0
	next    = mined_text
	while match:
		# get the number
		number     = next[match.start():match.end()]
		number     = number[number.find(' ') + 1:]
		index      = number.rfind(' ')
		if index == -1:
			index = number.rfind('TH')
			if index == -1:
				index = number.rfind('ST')
				if index == -1:
					index = number.rfind('ND')
					if index == -1:
						index = number.rfind('RD')
		if index > -1:
			number = number[:index] 
		number     = days[int(number) - 1]
		
		# replace number
		mined_text = mined_text[:start + match.start() + next[match.start():match.end()].find(' ') + 1] + number + mined_text[start + match.end():]
		start      += match.start() + len(number) + next[match.start():].find(' ') + 1
		next       = next[match.end():]
		match      = date_re.search(next)
	del date_re
	
	# delete phone numbers
	if not options.quiet:
		print '  Deleting phone numbers'
	phone_re = re.compile(r'(1(-|\.))?((\([0-9]{3}\) ?)|([0-9]{3}(\.|-)))[0-9]{3}(?(2)\2|(?(6)\6|(\.|-)))[0-9]{4}')
	match    = phone_re.search(mined_text)
	start    = 0
	next     = mined_text
	while match:
		mined_text = mined_text[:start + match.start()] + mined_text[start + match.end():]
		start      += match.start()
		next       = next[match.end():]
		match      = phone_re.search(next)
	del phone_re
	
	# replace [num]-[num] with [num] to [num]
	mined_text = re.sub(r'(?<=[0-9])\s*-\s*(?=[0-9])', ' TO ', mined_text)
	
	# replace ¼
	mined_text = re.sub(r'(?<=[0-9])¼',  ' AND A QUARTER', mined_text)
	mined_text = re.sub(r'(?<=A|1) ¼',   ' QUARTER',       mined_text)
	mined_text = re.sub(r'(?<=2|3) ¼S?', ' QUARTERS',      mined_text)
	mined_text = re.sub(r'ONE ¼',        'ONE QUARTER',    mined_text)
	mined_text = re.sub(r'TWO ¼S?',      'TWO QUARTERS',   mined_text)
	mined_text = re.sub(r'THREE ¼S?',    'THREE QUARTERS', mined_text)
	mined_text = re.sub(r'\s*¼S\s*',     ' QUARTERS ',     mined_text)
	mined_text = re.sub(r'\s*¼\s*',      ' QUARTER ',      mined_text)
	
	# replace ½
	mined_text = re.sub(r'(?<=[0-9])½',  ' AND A HALF',    mined_text)
	mined_text = re.sub(r'\s*½S\s*',     ' HALVES ',       mined_text)
	mined_text = re.sub(r'\s*½\s*',      ' HALF ',         mined_text)
	
	# delete email addresses
	if not options.quiet:
		print '  Deleting email addresses'
	email_re = re.compile(r'\b[A-Z0-9\._%+\-]+@[A-Z0-9\.\-]+\.[A-Z]{2,4}\b')
	match    = email_re.search(mined_text)
	start    = 0
	next     = mined_text
	while match:
		mined_text = mined_text[:start + match.start()] + mined_text[start + match.end():]
		start      += match.start()
		next       = next[match.end():]
		match      = email_re.search(next)
	del email_re
	
	# replace common units
	if not options.quiet:
		print '  Replacing unit abbreviations'
	mined_text = re.sub(r'\s*/\s*GAL(\.|\b)',                         ' PER GALLON',        mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )GAL(\.|\b)',                 ' GALLON',            mined_text)
	mined_text = re.sub(r'(?<=\bONE )GAL(\.|\b)',                     ' GALLON',            mined_text)
	mined_text = re.sub(r'\bGAL(\.|\b)',                              ' GALLONS',           mined_text)
	mined_text = re.sub(r'\bLBS(\.|\b)',                              ' POUNDS',            mined_text)
	mined_text = re.sub(r'\s*/\s*LB(\.|\b)',                          ' PER POUND',         mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )LB(\.|\b)',                  ' POUND',             mined_text)
	mined_text = re.sub(r'(?<=\bONE )LB(\.|\b)',                      ' POUND',             mined_text)
	mined_text = re.sub(r'\bLB(\.|\b)',                               ' POUND',             mined_text)
	mined_text = re.sub(r'\s*/\s*FL(\.|\b)',                          ' PER FLUID',         mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )FL(\.|\b)',                  ' FLUID',             mined_text)
	mined_text = re.sub(r'(?<=\bONE )FL(\.|\b)',                      ' FLUID',             mined_text)
	mined_text = re.sub(r'\bFL(\.|\b)',                               ' FLUID',             mined_text)
	mined_text = re.sub(r'\s*/\s*OZ(\.|\b)',                          ' PER OUNCE',         mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )OZ(\.|\b)',                  ' OUNCE',             mined_text)
	mined_text = re.sub(r'(?<=\bONE )OZ(\.|\b)',                      ' OUNCE',             mined_text)
	mined_text = re.sub(r'\bOZ(\.|\b)',                               ' OUNCES',            mined_text)
	mined_text = re.sub(r'\s*/\s*G(\.|\b)',                           ' PER GRAM',          mined_text)
	# mined_text = re.sub(r'(?<=[^0-9\.]1 )G(\.|\b)',                   ' GRAM',              mined_text)
	# mined_text = re.sub(r'(?<=\bONE )G(\.|\b)',                       ' GRAM',              mined_text)
	# mined_text = re.sub(r'(?<=[0-9] )G(\.|\b)',                       ' GRAMS',             mined_text)
	mined_text = re.sub(r'\s*/\s*MCG(\.|\b)',                         ' PER MICROOGRAM',    mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MCG(\.|\b)',                 ' MICROGRAM',         mined_text)
	mined_text = re.sub(r'(?<=\bONE )MCG(\.|\b)',                     ' MICROGRAM',         mined_text)
	mined_text = re.sub(r'\bMCG(\.|\b)',                              ' MICROGRAMS',        mined_text)
	mined_text = re.sub(r'\s*/\s*MG(\.|\b)',                          ' PER MILLIGRAM',     mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MG(\.|\b)',                  ' MILLIGRAM',         mined_text)
	mined_text = re.sub(r'(?<=\bONE )MG(\.|\b)',                      ' MILLIGRAM',         mined_text)
	mined_text = re.sub(r'\bMG(\.|\b)',                               ' MILLIGRAMS',        mined_text)
	mined_text = re.sub(r'\s*/\s*KG(\.|\b)',                          ' PER KILOGRAM',      mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )KG(\.|\b)',                  ' KILOGRAM',          mined_text)
	mined_text = re.sub(r'(?<=\bONE )KG(\.|\b)',                      ' KILOGRAM',          mined_text)
	mined_text = re.sub(r'\bKG(\.|\b)',                               ' KILOGRAMS',         mined_text)
	mined_text = re.sub(r'\s*/\s*PT(\.|\b)',                          ' PER PINT',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )PT(\.|\b)',                  ' PINT',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )PT(\.|\b)',                      ' PINT',              mined_text)
	mined_text = re.sub(r'(?<=([1-9][0-9])|([^0-9][2-9])) PT(\.|\b)', ' PINTS',             mined_text)
	mined_text = re.sub(r'\s*/\s*L(\.|\b)',                           ' PER LITER',         mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )L(\.|\b)',                   ' LITER',             mined_text)
	mined_text = re.sub(r'(?<=\bONE )L(\.|\b)',                       ' LITER',             mined_text)
	mined_text = re.sub(r'(?<=[0-9] )L(\.|\b)',                       ' LITERS',            mined_text)
	mined_text = re.sub(r'\s*/\s*ML(\.|\b)',                          ' PER MILLILITER',    mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )ML(\.|\b)',                  ' MILLILITER',        mined_text)
	mined_text = re.sub(r'(?<=\bONE )ML(\.|\b)',                      ' MILLILITER',        mined_text)
	mined_text = re.sub(r'\bML(\.|\b)',                               ' MILLILITERS',       mined_text)
	mined_text = re.sub(r'\s*/\s*KL(\.|\b)',                          ' PER KILOLITER',     mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )KL(\.|\b)',                  ' KILOLITER',         mined_text)
	mined_text = re.sub(r'(?<=\bONE )KL(\.|\b)',                      ' KILOLITER',         mined_text)
	mined_text = re.sub(r'\bKL(\.|\b)',                               ' KILOLITERS',        mined_text)
	mined_text = re.sub(r'\s*/\s*MM(\.|\b)',                          ' PER MILLIMETER',    mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MM(\.|\b)',                  ' MILLIMETER',        mined_text)
	mined_text = re.sub(r'(?<=\bONE )MM(\.|\b)',                      ' MILLIMETER',        mined_text)
	mined_text = re.sub(r'\bMM(\.|\b)',                               ' MILLIMETERS',       mined_text)
	mined_text = re.sub(r'\bMILLIMETERS²',                            ' SQUARE MILLIMETERS',mined_text)
	mined_text = re.sub(r'\bMILLIMETERS³',                            ' CUBIC MILLIMETERS', mined_text)
	mined_text = re.sub(r'\bMILLIMETER²',                             ' SQUARE MILLIMETER', mined_text)
	mined_text = re.sub(r'\bMILLIMETER³',                             ' CUBIC MILLIMETER',  mined_text)
	mined_text = re.sub(r'\s*/\s*CM(\.|\b)',                          ' PER CENTIMETER',    mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )CM(\.|\b)',                  ' CENTIMETER',        mined_text)
	mined_text = re.sub(r'(?<=\bONE )CM(\.|\b)',                      ' CENTIMETER',        mined_text)
	mined_text = re.sub(r'\bCM(\.|\b)',                               ' CENTIMETERS',       mined_text)
	mined_text = re.sub(r'\bCENTIMETERS²',                            ' SQUARE CENTIMETERS',mined_text)
	mined_text = re.sub(r'\bCENTIMETERS³',                            ' CUBIC CENTIMETERS', mined_text)
	mined_text = re.sub(r'\bCENTIMETER²',                             ' SQUARE CENTIMETER', mined_text)
	mined_text = re.sub(r'\bCENTIMETER³',                             ' CUBIC CENTIMETER',  mined_text)
	mined_text = re.sub(r'\s*/\s*KM(\.|\b)',                          ' PER KILOMETER',     mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )KM(\.|\b)',                  ' KILOMETER',         mined_text)
	mined_text = re.sub(r'(?<=\bONE )KM(\.|\b)',                      ' KILOMETER',         mined_text)
	mined_text = re.sub(r'\bKM(\.|\b)',                               ' KILOMETERS',        mined_text)
	mined_text = re.sub(r'\bKILOMETERS²',                             ' SQUARE KILOMETERS', mined_text)
	mined_text = re.sub(r'\bKILOMETERS³',                             ' CUBIC KILOMETERS',  mined_text)
	mined_text = re.sub(r'\bKILOMETER²',                              ' SQUARE KILOMETER',  mined_text)
	mined_text = re.sub(r'\bKILOMETER³',                              ' CUBIC KILOMETER',   mined_text)
	mined_text = re.sub(r'\s*/\s*M(\.|\b)',                           ' PER METER',         mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )M(\.|\b)',                   ' METER',             mined_text)
	mined_text = re.sub(r'(?<=\bONE )M(\.|\b)',                       ' METER',             mined_text)
	mined_text = re.sub(r'(?<=[0-9] )M(\.|\b)',                       ' METERS',            mined_text)
	mined_text = re.sub(r'\bMETERS²',                                 ' SQUARE METERS',     mined_text)
	mined_text = re.sub(r'\bMETERS³',                                 ' CUBIC METERS',      mined_text)
	mined_text = re.sub(r'\bMETER²',                                  ' SQUARE METER',      mined_text)
	mined_text = re.sub(r'\bMETER³',                                  ' CUBIC METER',       mined_text)
	mined_text = re.sub(r'\s*/\s*IN(\.|\b)',                          ' PER INCH',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )IN\.',                       ' INCH',              mined_text)
	mined_text = re.sub(r'(?<=[0-9]) IN\.',                           ' INCHES',            mined_text)
	mined_text = re.sub(r'\bINCHES²',                                 ' SQUARE INCHES',     mined_text)
	mined_text = re.sub(r'\bINCHES³',                                 ' CUBIC INCHES',      mined_text)
	mined_text = re.sub(r'\bINCH²',                                   ' SQUARE INCH',       mined_text)
	mined_text = re.sub(r'\bINCH³',                                   ' CUBIC INCH',        mined_text)
	mined_text = re.sub(r'\s*/\s*FT(\.|\b)',                          ' PER FOOT',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )FT(\.|\b)',                  ' FOOT',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )FT(\.|\b)',                      ' FOOT',              mined_text)
	mined_text = re.sub(r'\bFT(\.|\b)',                               ' FEET',              mined_text)
	mined_text = re.sub(r'\bFEET²',                                   ' SQUARE FEET',       mined_text)
	mined_text = re.sub(r'\bFEET³',                                   ' CUBIC FEET',        mined_text)
	mined_text = re.sub(r'\bFOOT²',                                   ' SQUARE FOOT',       mined_text)
	mined_text = re.sub(r'\bFOOT³',                                   ' CUBIC FOOT',        mined_text)
	mined_text = re.sub(r'\s*/\s*YD(\.|\b)',                          ' PER YARD',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )YD(\.|\b)',                  ' YARD',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )YD(\.|\b)',                      ' YARD',              mined_text)
	mined_text = re.sub(r'\bYD(\.|\b)',                               ' YARDS',             mined_text)
	mined_text = re.sub(r'\s*/\s*MI(\.|\b)',                          ' PER MILE',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MI(\.|\b)',                  ' MILE',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )MI(\.|\b)',                      ' MILE',              mined_text)
	mined_text = re.sub(r'\bMI(\.|\b)',                               ' MILES',             mined_text)
	mined_text = re.sub(r'\s*/\s*HR(\.|\b)',                          ' PER HOUR',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )HR(\.|\b)',                  ' HOUR',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )HR(\.|\b)',                      ' HOUR',              mined_text)
	mined_text = re.sub(r'\bHR(\.|\b)',                               ' HOURS',             mined_text)
	mined_text = re.sub(r'\s*/\s*MIN(\.|\b)',                         ' PER MINUTE',        mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MIN(\.|\b)',                 ' MINUTE',            mined_text)
	mined_text = re.sub(r'(?<=\bONE )MIN(\.|\b)',                     ' MINUTE',            mined_text)
	mined_text = re.sub(r'(?<=[0-9] )MIN(\.|\b)',                     ' MINUTES',           mined_text)
	mined_text = re.sub(r'\bMINUTES²',                                ' MINUTES SQUARED',   mined_text)
	mined_text = re.sub(r'\bMINUTE²',                                 ' MINUTE SQUARED',    mined_text)
	mined_text = re.sub(r'\s*/\s*S(\.|\b)',                           ' PER SECOND',        mined_text)
	mined_text = re.sub(r'\s*/\s*SEC(\.|\b)',                         ' PER SECOND',        mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )((SEC)|S)(\.|\b)',           ' SECOND',            mined_text)
	mined_text = re.sub(r'(?<=\bONE )((SEC)|S)(\.|\b)',               ' SECOND',            mined_text)
	mined_text = re.sub(r'(?<=[0-9] )((SEC)|S)(\.|\b)',               ' SECONDS',           mined_text)
	mined_text = re.sub(r'\bSECONDS²',                                ' SECONDS SQUARED',   mined_text)
	mined_text = re.sub(r'\bSECOND²',                                 ' SECOND SQUARED',    mined_text)
	mined_text = re.sub(r'\s*/\s*HZ(\.|\b)',                          ' PER HERTZ',         mined_text)
	mined_text = re.sub(r'\bHZ(\.|\b)',                               ' HERTZ',             mined_text)
	mined_text = re.sub(r'\s*/\s*V(\.|\b)',                           ' PER VOLT',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )V(\.|\b)',                   ' VOLT',              mined_text)
	mined_text = re.sub(r'(?<=\bONE )V(\.|\b)',                       ' VOLT',              mined_text)
	mined_text = re.sub(r'\bV(\.|\b)',                                ' VOLTS',             mined_text)
	mined_text = re.sub(r'\s*/\s*DBA(\.|\b)',                         ' PER DECIBEL',       mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )DBA(\.|\b)',                 ' DECIBEL',           mined_text)
	mined_text = re.sub(r'(?<=\bONE )DBA(\.|\b)',                     ' DECIBEL',           mined_text)
	mined_text = re.sub(r'\bDBA(\.|\b)',                              ' DECIBELS',          mined_text)
	mined_text = re.sub(r'\s*/\s*DB(\.|\b)',                          ' PER DECIBEL',       mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )DB(\.|\b)',                  ' DECIBEL',           mined_text)
	mined_text = re.sub(r'(?<=\bONE )DB(\.|\b)',                      ' DECIBEL',           mined_text)
	mined_text = re.sub(r'\bDB(\.|\b)',                               ' DECIBELS',          mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )PPM(\.|\b)',                 ' PART PER MILLION',  mined_text)
	mined_text = re.sub(r'(?<=\bONE )PPM(\.|\b)',                     ' PART PER MILLION',  mined_text)
	mined_text = re.sub(r'\bPPM(\.|\b)',                              ' PARTS PER MILLION', mined_text)
	mined_text = re.sub(r'(?<=[^0-9\.]1 )MMOL(\.|\b)',                ' MILLIMOLE',         mined_text)
	mined_text = re.sub(r'(?<=\bONE )MMOL(\.|\b)',                    ' MILLIMOLE',         mined_text)
	mined_text = re.sub(r'\bMMOL(\.|\b)',                             ' MILLIMOLES',        mined_text)
	
	# replace common abbreviations that contain periods
	if not options.quiet:
		print '  Replacing common abbreviations'
	mined_text = re.sub(r'\bALT\.',        'ALTITUDE',        mined_text)
	mined_text = re.sub(r'\bAPT(\.|\b)',   'APARTMENT',       mined_text)
	mined_text = re.sub(r'\bAPPT(\.|\b)',  'APPOINTMENT',     mined_text)
	mined_text = re.sub(r'\bCOMDR(\.|\b)', 'COMMANDER',       mined_text)
	mined_text = re.sub(r'\bCPL(\.|\b)',   'CORPORAL',        mined_text)
	mined_text = re.sub(r'\bDEPT(\.|\b)',  'DEPARTMENT',      mined_text)
	mined_text = re.sub(r'\bDIV(\.|\b)',   'DIVISION',        mined_text)
	mined_text = re.sub(r'\bDR(\.|\b)',    'DOCTOR',          mined_text)
	mined_text = re.sub(r'\bEST(\.|\b)',   'ESTABLISHED',     mined_text)
	mined_text = re.sub(r'\bE\.?G(\.|\b)', 'ESTIMATED GUESS', mined_text)
	mined_text = re.sub(r'\bI\.?E(\.|\b)', 'IN EXAMPLE',      mined_text)
	# mined_text = re.sub(r'\bPT(\.|\b)',    'PART',            mined_text) --> could be abbreviation for patient
	mined_text = re.sub(r'\bSGT(\.|\b)',   'SERGEANT',        mined_text)
	mined_text = re.sub(r'\bSR(\.|\b)',    'SENIOR',          mined_text)
	mined_text = re.sub(r'\bSQ(\.|\b)',    'SQUARE',          mined_text)
	mined_text = re.sub(r'\bVOL(\.|\b)',   'VOLUME',          mined_text)
	mined_text = re.sub(r'\bWT(\.|\b)',    'WEIGHT',          mined_text)
	mined_text = re.sub(r'\bN/A\b',        'NOT APPLICABLE',  mined_text)
	mined_text = re.sub(r'\bB/P\b',        'BP',              mined_text)
	mined_text = re.sub(r'\bY/O\b',        'YEAR OLD',        mined_text)
	mined_text = re.sub(r'\bW/U\b',        'WORKUP',          mined_text)
	mined_text = re.sub(r'\bW/O\b',        'WITHOUT',         mined_text)
	mined_text = re.sub(r'\bW/',           'WITH',            mined_text)
	mined_text = re.sub(r'\bPT(\.|\b)',    'PATIENT',         mined_text)
	mined_text = re.sub(r'\bPTS(\.|\b)',   'PATIENTS',        mined_text)
	mined_text = re.sub(r'\bRD(\.|\b)',    'ROAD',            mined_text)
	mined_text = re.sub(r'\bAVE(\.|\b)',   'AVENUE',          mined_text)
	mined_text = re.sub(r'\bBLVD(\.|\b)',  'BOULEVARD',       mined_text)
	mined_text = re.sub(r'\bST(\.|\b)',    'STREET',          mined_text)
	mined_text = re.sub(r'\bEA(\.|\b)',    'EACH',            mined_text)
	mined_text = re.sub(r'\bE(\.|\b)',     'EACH',            mined_text)
	mined_text = re.sub(r'\bU\.S\.',       'U S',             mined_text)
	mined_text = re.sub(r'\bO\.?K\b\.?',   'OKAY',            mined_text)
	mined_text = re.sub(r'\bDX\b',         'DIAGNOSIS',       mined_text)
	mined_text = re.sub(r'\bRX\b',         'PRESCRIPTION',    mined_text)
	mined_text = re.sub(r'\bTX\b',         'TREATMENT',       mined_text)
	
	# replace single-quoted strings, ignoring contractions and cases of possession
	mined_text = re.sub(r'’|‘',                       '\'', mined_text)
	mined_text = re.sub(r'(?<=[^A-Z])\'',             '',   mined_text)
	mined_text = re.sub(r'(?<=[A-RT-Z])\'(?=[^A-Z])', '',   mined_text)
	
	# replace symbols
	if not options.quiet:
		print '  Replacing symbols'
	mined_text = re.sub(r'\s*#\s*',          ' NUMBER ',                mined_text)
	mined_text = re.sub(r"\s*&\s*",          ' AND ',                   mined_text)
	mined_text = re.sub(r"\s*%\s*",          ' PERCENT ',               mined_text)
	mined_text = re.sub(r"\s*=\s*",          ' EQUALS ',                mined_text)
	mined_text = re.sub(r"\s*@\s*",          ' AT ',                    mined_text)
	mined_text = re.sub(r'\s*\+\s*',         ' PLUS ',                  mined_text)
	mined_text = re.sub(r'\s*<\s*',          ' LESS THAN ',             mined_text)
	mined_text = re.sub(r'\s*(≤|(<=))\s*',   ' LESS THAN OR EQUAL TO ', mined_text)
	mined_text = re.sub(r'\s*>\s*',          ' GREATER THAN ',          mined_text)
	mined_text = re.sub(r'\s*(≥|(>=))\s*',   ' LESS THAN OR EQUAL TO ', mined_text)
	mined_text = re.sub(r'\s*/\s*',          ' OVER ',                  mined_text)# make this OR?
	mined_text = re.sub(r'\s*²\s*',          ' SQUARED ',               mined_text)
	mined_text = re.sub(r'\s*(°|º)\s*C\s*',  ' DEGREES CELSIUS ',       mined_text)
	mined_text = re.sub(r'\s*(°|º)\s*F\s*',  ' DEGREES FARENHEIT ',     mined_text)
	mined_text = re.sub(r'\s*(°|º)\s*',      ' DEGREES ',               mined_text)
	mined_text = re.sub(r'\s*±\s*',          ' PLUS OR MINUS ',         mined_text)
	mined_text = re.sub(r'ﬁ',                'FI',                      mined_text)
	mined_text = re.sub(r'ﬀ',                'FF',                      mined_text)
	mined_text = re.sub(r'ﬃ',                'FFI',                    mined_text)
	mined_text = re.sub(r'ﬂ',                'FL',                      mined_text)
	mined_text = re.sub(r'¥|§',              '$',                       mined_text)
	
	# ignore periods signifying an initial
	mined_text = re.sub(r'(?<= [A-Z])\.', '', mined_text)
	
	# split sentences
	if not options.quiet:
		print '  Splitting sentences'
	mined_text = re.sub(r'(\.{3})|((?<![0-9\-])\.(?![0-9]))|;|\?|!|…', '\n', mined_text)
	
	# ignore sentences with large numbers
	mined_text = mined_text.splitlines()
	if not options.quiet:
		print '  Ignoring sentences with large numbers'
		if options.verbose:
			print '    # Sentences Before: ' + str(len(mined_text))
	too_big_re = re.compile(r'[0-9]{5,}')
	for sentence in mined_text:
		if too_big_re.match(sentence):
			mined_text.remove(sentence)
	if not options.quiet and options.verbose:
		print '    # Sentences After: ' + str(len(mined_text))
	mined_text = '\n'.join(mined_text)
	
	# this prevents things like a-2 changing to anegative two
	mined_text = re.sub(r'(?<=[A-Z])-(?=[0-9])', ' ', mined_text)
	mined_text = re.sub(r'(?<=[0-9])-(?=[A-Z])', ' ', mined_text)
	
	# remove commas between digits
	mined_text = re.sub(r'(?<=[0-9]),(?=[0-9])', '', mined_text)
	
	# replace each number with its word equivalent
	if not options.quiet:
		print '  Replacing numbers'
	mined_text = re.sub(r'20\'?S\b',          ' TWENTIES',  mined_text)
	mined_text = re.sub(r'30\'?S\b',          ' THIRTIES',  mined_text)
	mined_text = re.sub(r'40\'?S\b',          ' FORTIES',   mined_text)
	mined_text = re.sub(r'50\'?S\b',          ' FIFTIES',   mined_text)
	mined_text = re.sub(r'60\'?S\b',          ' SIXTIES',   mined_text)
	mined_text = re.sub(r'70\'?S\b',          ' SEVENTIES', mined_text)
	mined_text = re.sub(r'80\'?S\b',          ' EIGHTIES',  mined_text)
	mined_text = re.sub(r'90\'?S\b',          ' NINETIES',  mined_text)
	mined_text = re.sub(r'\bII\b',            'TWO',        mined_text)
	mined_text = re.sub(r'\bIII\b',           'THREE',      mined_text)
	# FOUR = IV, which is common in medical terminology -> must evaluate cases by hand
	mined_text = re.sub(r'(?<![0-9]) ?\bV\b', 'FIVE',       mined_text)
	mined_text = re.sub(r'\bVI\b',            'SIX',        mined_text)
	mined_text = re.sub(r'\bVII\b',           'SEVEN',      mined_text)
	mined_text = re.sub(r'\bVIII\b',          'EIGHT',      mined_text)
	mined_text = re.sub(r'\bIX\b',            'NINE',       mined_text)
	# TEN = X, which is a common abbreviation for times -> must evaluate cases by hand
	number_re  = re.compile(r'-?(((([1-9][0-9]*|0))?\.[0-9]*)|([1-9][0-9]*)|0)')
	match      = number_re.search(mined_text)
	start      = 0
	next       = mined_text
	while match:
		word_string = numToWordString(next[match.start():match.end()])
		mined_text  = mined_text[:start + match.start()] + word_string + mined_text[start + match.end():]
		start      += len(word_string) + match.start()
		next        = next[match.end():]
		match       = number_re.search(next)
	del next
	
	# replace ONEst, TWOnd, THREErd, FIVEth, EIGHTth, TWELVEth, TWENTYth,
	# THIRTYth, FOURTYth, FIFTYth, SIXTYth, SEVENTYth, EIGHTYth, NINETYth
	if not options.quiet:
		print '  Replacing order specifiers (i.e. 1st, 2nd, etc.)'
	mined_text = re.sub(r'\bONE ST\b',       'FIRST',       mined_text)
	mined_text = re.sub(r'\bTWO ND\b',       'SECOND',      mined_text)
	mined_text = re.sub(r'\bTHREE RD\b',     'THIRD',       mined_text)
	mined_text = re.sub(r'\bFOUR TH\b',      'FOURTH',      mined_text)
	mined_text = re.sub(r'\bFIVE TH\b',      'FIFTH',       mined_text)
	mined_text = re.sub(r'\bSIX TH\b',       'SIXTH',       mined_text)
	mined_text = re.sub(r'\bSEVEN TH\b',     'SEVENTH',     mined_text)
	mined_text = re.sub(r'\bEIGHT TH\b',     'EIGHTH',      mined_text)
	mined_text = re.sub(r'\bNINE TH\b',      'NINTH',       mined_text)
	mined_text = re.sub(r'\bTEN TH\b',       'TENTH',       mined_text)
	mined_text = re.sub(r'\bELEVEN TH\b',    'ELEVENTH',    mined_text)
	mined_text = re.sub(r'\bTWELVE TH\b',    'TWELFTH',     mined_text)
	mined_text = re.sub(r'\bTHIRTEEN TH\b',  'THIRTEENTH',  mined_text)
	mined_text = re.sub(r'\bFOURTEEN TH\b',  'FOURTEENTH',  mined_text)
	mined_text = re.sub(r'\bFIFTEEN TH\b',   'FIFTEENTH',   mined_text)
	mined_text = re.sub(r'\bSIXTEEN TH\b',   'SIXTEENTH',   mined_text)
	mined_text = re.sub(r'\bSEVENTEEN TH\b', 'SEVENTEENTH', mined_text)
	mined_text = re.sub(r'\bEIGHTEEN TH\b',  'EIGHTEENTH',  mined_text)
	mined_text = re.sub(r'\bNINETEEN TH\b',  'NINETEENTH',  mined_text)
	mined_text = re.sub(r'\bTWENTY TH\b',    'TWENTIETH',   mined_text)
	mined_text = re.sub(r'\bTHIRTY TH\b',    'THIRTIETH',   mined_text)
	mined_text = re.sub(r'\bFORTY TH\b',     'FOURTIETH',   mined_text)
	mined_text = re.sub(r'\bFIFTY TH\b',     'FIFTIETH',    mined_text)
	mined_text = re.sub(r'\bSIXTY TH\b',     'SIXTIETH',    mined_text)
	mined_text = re.sub(r'\bSEVENTY TH\b',   'SEVENTIETH',  mined_text)
	mined_text = re.sub(r'\bEIGHTY TH\b',    'EIGHTIETH',   mined_text)
	mined_text = re.sub(r'\bNINETY TH\b',    'NINETIETH',   mined_text)
	mined_text = re.sub(r'\bHUNDRED TH\b',   'HUNDREDTH',   mined_text)
	mined_text = re.sub(r'\bTHOUSAND TH\b',  'THOUSANDTH',  mined_text)
	
	# space out hyphenated words
	mined_text = re.sub(r'(?<=[A-Z])-(?=[A-Z])', ' ', mined_text)
	
	# remove any remaining non-ASCII characters
	mined_text = ''.join(i for i in mined_text if (ord(i) > 64 and ord(i) < 91) or i == '\n' or i == '\'' or i == '$')
	
	# remove superfluous space
	mined_text = re.sub(r' {2,}', ' ', mined_text)
	
	# remove all empty lines from the mined text
	if not options.quiet:
		print '  Removing empty lines'
	mined_text = re.sub('\n{2,}', '\n', mined_text)
	
	# append cleaned text to file if requested
	if options.cleaned:
		if not options.quiet:
			print 'Appending cleaned sentences'
		f = open(options.cleaned, 'a')
		f.write(mined_text)
		f.close()
	
	# apply initial filter to get rid of any sentences that are obviously useless
	if not options.quiet:
		print 'Performing initial filter'
	useless_re = [re.compile(r'\bCOPYRIGHT'),
				  re.compile(r'\bALL\s+RIGHTS\s+RESERVED'),
				  re.compile(r'\bTHIS\s+ARTICLE\s+HAS(\s+NOT)?\s+BEEN\s+CITED'),
				  re.compile(r'\b((KILO)|(MEGA)|(GIGA)|(TERA))?BYTE'),
				  re.compile(r'\bISOTOPE'),
				  re.compile(r'\bGADOLINIUM'),
				  re.compile(r'\bBLOG'),
				  re.compile(r'\bDVD'),
				  re.compile(r'\b([A-Z\']+)(\s\1){2,}'),
				  re.compile(r'\$'),
				  re.compile(r'\bBUDGET'),
				  re.compile(r'\bPHYSICS'),
				  re.compile(r'\bPRICE'),
				  re.compile(r'\bCID\b'),
				  re.compile(r'\bHTML\b'),
				  re.compile(r'\bFISCAL'),
				  re.compile(r'\b([A-Z] ){4,}')]
	mined_text = mined_text.splitlines()
	i = 0
	while i < len(mined_text):
		sentence = mined_text[i]
		words    = sentence.split()
		numbers  = 0
		
		if len(words) > 50:
			numbers = len(words)
		
		if numbers == 0:
			for useless in useless_re:
				if useless.search(sentence):
					numbers = len(words)
					break
		
		if numbers == 0:
			for word in words:
				if word in units or word in tens or word in teens or word in thousands or word == 'HUNDRED':
					numbers += 1
		
		if numbers >= .3 * len(words):
			mined_text.pop(i)
			i -= 1
		i += 1
	mined_text = '\n'.join(mined_text)
	
	# clean up
	del useless_re
	
	# filter out bad sentences
	if options.prev_mined:
		try:
			f                = open(options.append, 'r')
			previously_mined = options.append
			f.close()
		except:
			previously_mined = None
	else:
		previously_mined = None
	if options.nonincremental:
		if not options.quiet:
			print 'Filtering sentences non-incrementally'
		sentences = nonincrementalFilter(options.seed, previously_mined, mined_text, options.quiet)
	else:
		if not options.quiet:
			print 'Filtering sentences incrementally'
		sentences = incrementalFilter(options.seed, previously_mined, mined_text, options.quiet)
	
	# append to file if requested, otherwise print text
	# only append new sentences
	mined_text     = ''
	f              = open(options.seed, 'r')
	seed_sentences = set(f.read().splitlines())
	f.close()
	all_sentences  = set(sentences.splitlines())
	filtered       = all_sentences - seed_sentences
	if previously_mined:
		f                = open(previously_mined, 'r')
		previously_mined = set(f.read().splitlines())
		f.close()
		filtered -= previously_mined
		del previously_mined
	for sentence in filtered:
		mined_text += sentence.strip() + '\n'
	if options.append:
		f = open(options.append, 'a')
		f.write(mined_text)
		f.close()
	else:
		print mined_text
	
	if not options.quiet:
		print 'Added ' + str(len(filtered)) + ' sentences'
	
	# clean up
	del f
	del mined_text
	del all_sentences
	del seed_sentences
	del sentences
	
	exit()

if __name__ == '__main__':
	main()
