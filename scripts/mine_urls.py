#!/usr/bin/env python
import os, sys, re, optparse, random, operator, unicodedata, time, uuid
from pattern.web import URL, URLError, plaintext, URLTimeout

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams

if sys.version_info[0] == 3:
	from urllib.request import HTTPCookieProcessor, Request, build_opener
	from urllib.parse import quote
	from http.cookiejar import CookieJar
else:
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
		print 'Must first install BeautifulSoup ... Sorry!'
		sys.exit(1)

# custom in-house libraries
from files import yieldfiles
from timeouts import timeout, TimeoutException, cancelTimeout#, timeoutIn, resetTimeoutHandler


# Support unicode in both Python 2 and 3. In Python 3, unicode is str.
if sys.version_info[0] == 3:
	unicode = str
	encode = lambda s: s
else:
	encode = lambda s: s.encode('utf-8')

# register a custom codec error handler
def codec_error_handler_remove(e):
	from pprint import pprint
	pprint(e)
	return (u'', e.start + 1)

n = 3

# generates a (n word tuple: count) dictionary from a list of
# text files.  text files must be only alphabetic characters 
# and white space
def getCounts(f):
	ngrams = {}
	
	f    = open(f)
	line = f.readline()
	while line:
		line     = line.rstrip()
		wordList = line.split()
		
		for i in range(len(wordList) - n + 1):
			gram = tuple(wordList[i:i+n])
			
			if gram in ngrams:
				ngrams[gram] += 1
			else:
				ngrams[gram] = 1
		
		line = f.readline()
	f.close()
	return ngrams


# returns an integer representing the total count of all n-grams
def getTotalCount(dict):
	sortedDict = sorted(dict.iteritems(), key=operator.itemgetter(1), reverse=True)
	ct = 0
	
	for entry in sortedDict:
		ct += entry[1]
	
	return ct
	

# selects a random key from a dictionary, weighted by the values.
# values must be integers.
def weightedRandom(dict):
	r = random.uniform(0, sum(dict.itervalues()))
	s = 0.0
	for k, w in dict.iteritems():
		s += w
		if r < s: return k
	return k


# This class will query Google's search engine and return the resulting HTML page.
class GoogleQuerier(object):
	GOOGLE_URL = 'https://www.google.com/search?client=safari&rls=en&q=%(query)s&ie=UTF-8&oe=UTF-8&num=%(count)s'
	USER_AGENT = 'Mozilla/5.0 (X11; U; FreeBSD i386; en-US; rv:1.9.2.9) Gecko/20100913 Firefox/3.6.9'
	
	def __init__(self, count=10, tries=3, timeout_wait=10):
		# Google doesn't support more than 100 results per page
		self.count        = min(count, 100)
		self.opener       = build_opener(HTTPCookieProcessor(CookieJar()))
		self.timeout_wait = timeout_wait
		self.tries        = tries
	
	def query(self, query):
		url     = self.GOOGLE_URL % {'query': quote(encode(query)), 'count': str(self.count)}
		timeout = self.tries # number of tries before giving up
		while timeout > 0:
			try:
				return self.opener.open(Request(url=url, headers={'User-Agent': self.USER_AGENT})).read()
			except KeyboardInterrupt:
				raise
			except:
				timeout -= 1
				if timeout > 0:
					time.sleep(self.timeout_wait)
		return None


def parse_results_page(html):
	if html:
		soup = BeautifulSoup(html)
		for result in soup.findAll(is_result):
			url = parse_result(result)
			if url: # otherwise tag does not represent a proper result
				yield url
	else:
		yield None


# return value of None means the tag was not a webpage result (usually a collection of images that Google adds)
def parse_result(outer_tag):
	try:
		url = outer_tag.h3.a['href']
		if url.startswith('/url?q='):
			index = url.find('&sa=')
			url   = url[7:index]
			try:
				URL(url).open()
			except:
				index = url.find('%')
				if index > -1:
					url = url[:index]
			return url
		else: # tag does not represent a proper result
			return None
	except:
		return None


# This predicate function checks whether a BeatifulSoup Tag instance has a
# specific class attribute value.
def tag_has_class(tag, klass):
	res = tag.get('class') or []
	if type(res) != list:
		# BeautifulSoup 3 can return e.g. 'gs_md_wp gs_ttss',
		# so split -- conveniently produces a list in any case
		res = res.split()
	return klass in res


def is_result(tag):
	return tag.name == 'li' and tag_has_class(tag, 'g')


def parse_full_text(url, pdf_page_timeout):
	if url.find('pdf') != -1:
		return parsePDF(url, pdf_page_timeout)
	elif not url.endswith('.ppt') and not url.endswith('.pptx'):
		# download the html, grab only the plain text from it (remove tags, etc.)
		# then replace accented characters, etc. with their ascii equivalents
		return unicodedata.normalize('NFKD', plaintext(URL(url).open().read())).encode('ascii', 'ignore')


def parsePDF(url, pdf_page_timeout):
	# download the PDF
	unique_id = str(uuid.uuid4())
	f         = open(unique_id, 'wb')
	f.write(URL(url).download())
	f.close()
	
	# prepare to parse the PDF for text
	f       = open(unique_id, 'rb')
	rsrcmgr = PDFResourceManager(caching=True)
	outfp   = file(unique_id + '.txt', 'w')
	device  = TextConverter(rsrcmgr, outfp, codec='utf-8', laparams=LAParams(), imagewriter=None)
	
	try:
		# parse the PDF document
		interpreter = PDFPageInterpreter(rsrcmgr, device)
		
		for page in PDFPage.get_pages(f, set(), maxpages=0, password='', caching=True, check_extractable=True):
			try:
				with timeout(pdf_page_timeout) as timer:
					interpreter.process_page(page)
			except TimeoutException:
				continue
			finally:
				cancelTimeout()
	finally:
		f.close()
		device.close()
		outfp.close()
		
		# read in the resulting text
		f         = open(unique_id + '.txt', 'r')
		full_text = f.read()
		f.close()
		
		# remove the temporary files
		os.system('rm -f ' + unique_id + ' ' + unique_id + '.txt')
	
	return full_text


def main():
	options, args = parse_args()
	
	# read in previously mined urls to avoid duplicates
	previously_mined = set()
	with open(urlsFile, 'r') as f:
		for line in f:
			previously_mined.add(line.strip())
	
	ngrams  = getCounts(options.corpus)
	querier = GoogleQuerier(options.results)
	
	i = 0
	while True:
		query = ' '.join(weightedRandom(ngrams))
		for j in range(0,random.randint(0,2)):
			query = ' '.join((query, ' '.join(weightedRandom(ngrams))))
		if options.verbosity >= 1:
			print 'Query ' + str(i + 1) + ':' + ' '*(5 - len(str(i + 1))) + query
		
		num_mined_urls = 0
		num_downloaded = 0
		num_repeats    = 0
		num_failed     = 0
		for url in parse_results_page(querier.query(query)):
			if not url:
				if options.verbosity >= 2:
					print '  COULD NOT COMPLETE REQUEST'
				continue
			
			if options.verbosity >= 3:
				print '  ' + url
			
			if url in previously_mined:
				if options.verbosity >= 4:
					print '    REPEAT'
				num_repeats += 1
				continue
			previously_mined.add(url)
			num_mined_urls += 1
			
			# store the url in its own file
			with open(options.urls_file), 'a') as f:
				f.write(url + '\n')
			
			if download_text(url, options):
				num_downloaded += 1
			else:
				num_failed += 1
		
		if options.verbosity >= 2:
			print '  Mined:      ' + str(num_mined_urls)
			print '  Downloaded: ' + str(num_downloaded)
			print '  Repeats:    ' + str(num_repeats)
			print '  Failed:     ' + str(num_failed)
		
		# to help prevent Google from detecting that this is a bot
		random.seed(int(time.time()))
		time.sleep(random.randint(15, 45))
		i += 1


def download_text(url, options):
	try: # try to scrape all text from the url
		text = parse_full_text(url, options.pdf_page_timeout)
		with open(options.mined_file, 'a') as f:
			f.write(text + '\n')
		return True
	except URLTimeout:
		if options.verbosity >= 4:
			print '    TIMED OUT'
	except Exception as exception: # supress any errors with downloading
		if options.verbosity >= 4:
			print '    ', type(exception)
		with open(options.exceptions_file, 'a') as f:
			f.write(url + "\n")
			f.write(str(type(exception)) + "\n")
			f.write("\n")
	return None


def parse_args ():
	parser = optparse.OptionParser()
	parser.add_option('-c', '--corpus',
	                  help    = 'The seed corpus file to use.')
	parser.add_option('-u', '--urls-file',
	                  default = None,
	                  help    = 'Read previously mined urls from and append new urls to this file.')
	parser.add_option('-m', '--mined-file',
	                  default = None,
	                  help    = 'Append newly downloaded text to this file.')
	parser.add_option('-e', '--exceptions-file',
	                  default = 'exceptions',
	                  help    = 'File in which to store information about unhandled exceptions that were thrown. [exceptions]')
	parser.add_option('-p', '--pdf-page-timeout',
	                  type    = 'int',
	                  default = 5,
	                  help    = 'The maximum number of seconds that can be spent on parsing a single page in a PDF before ignoring the page. [5]')
	parser.add_option('-g', '--google-query-tries',
	                  type    = 'int',
	                  default = 3,
	                  help    = 'Number of tries for sending an individual query to Google before giving up. [3]')
	parser.add_option('-w', '--wait-on-fail',
	                  type    = 'int',
	                  default = 10,
	                  help    = 'Number of seconds to wait before retrying a failed attempt to query Google. [10]')
	parser.add_option('-r', '--results',
	                  type    = 'int',
	                  default = 20,
	                  help    = 'The number of results to use per query. [20]')
	parser.add_option('-v', '--verbosity',
	                  type    = 'int',
	                  default = 2,
	                  help    = 'How verbose the output should be (0 to 4 inclusive). [2]')
	return parser.parse_args()


if __name__ == '__main__':
	main()
