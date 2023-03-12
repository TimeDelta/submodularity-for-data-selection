#!/usr/bin/evn python
import os, optparse, unicodedata, tempfile
from pattern.web import URL, plaintext, HTTP404NotFound, HTTP403Forbidden, HTTPError, HTTP401Authentication, URLError

from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfparser import PDFSyntaxError

from timeouts import timeout, TimeoutException, cancelTimeout#, timeoutIn, resetTimeoutHandler

def parse_full_text(url, pdf_page_timeout):
	if url.find('pdf') != -1:
		return parsePDF(url, pdf_page_timeout)
	elif not url.endswith('.ppt') and not url.endswith('.pptx'):
		return unicodedata.normalize('NFKD', plaintext(URL(url).open().read())).encode('ascii', 'ignore')


def parsePDF(url, pdf_page_timeout):
	f = tempfile.TemporaryFile()
	f.write(URL(url).download())
	
	rsrcmgr = PDFResourceManager(caching=True)
	outfp   = tempfile.TemporaryFile()
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
		# read in the resulting text
		full_text = outfp.read()
		
		f.close()
		device.close()
		outfp.close()
	
	return full_text


def empty_dl_file(options):
	with open(options.download_file, 'w') as download_file:
		download_file.write('\n')


def main():
	# add options to the option parser
	parser = optparse.OptionParser()
	parser.add_option('-u', '--url-file',
	                  default = None,
	                  help    = 'File containing the url to parse for text.')
	parser.add_option('-d', '--download-file',
	                  default = None,
	                  help    = 'The file in which to store the text downloaded from the specified url.')
	parser.add_option('-p', '--pdf-page-timeout',
	                  type    = 'int',
	                  default = 3,
	                  help    = 'The maximum number of seconds that can be spent on parsing a single page in a PDF before ignoring the page. [3]')
	parser.add_option('-e', '--supress-errors',
	                  action  = 'store_true',
	                  default = None,
	                  help    = 'If an exception is encountered while downloading, parsing a PDF or converting unicode to plain text, don\'t raise an exception. If an exception does occur, information about it will be printed to stdout unless -q is specified.')
	parser.add_option('-q', '--quiet',
	                  action  = 'store_true',
	                  default = None,
	                  help    = 'Quiet Mode.')
	
	# parse options and arguments
	options, args = parser.parse_args()
	
	# clean up
	del parser
	
	try:
		with open(options.url_file, 'r') as f:
			url  = f.readline().strip()
			text = url + '\n' + parse_full_text(url, options.pdf_page_timeout)
		if not text:
			text = ''
		
		with open(options.download_file, 'w') as download_file:
			download_file.write(text + '\n')
	except HTTP404NotFound:
		empty_dl_file(options)
	except HTTP403Forbidden:
		empty_dl_file(options)
	except PDFSyntaxError:
		empty_dl_file(options)
	except HTTPError:
		empty_dl_file(options)
	except HTTP401Authentication:
		empty_dl_file(options)
	except URLError:
		empty_dl_file(options)
	except Exception as exception:
		if options.supress_errors:
			if not options.quiet:
				print options.url_file[options.url_file.rfind('/') + 1:] + ':', type(exception)
				print options.url_file[options.url_file.rfind('/') + 1:] + ':', exception.args
			text = ''
		else:
			raise

if __name__ == '__main__':
	main()
