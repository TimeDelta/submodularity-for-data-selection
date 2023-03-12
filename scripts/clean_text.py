#!/usr/bin/env python
# coding=utf-8
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# ! IMPORTANT ! Do NOT remove the second line of this file, you will break the code !
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
import re, optparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from multisub import MultiSub
from english_number_conversion import numToText

#################################################################################################

def main():
	# parse command line options
	parser = optparse.OptionParser(usage='python clean_text.py [options] [<input_file>]')
	parser.add_option('-s', '--start-from',
	                  default = 1,
	                  type    = 'int',
	                  help    = 'Start processing at the Nth sentence, ignoring all sentences before it (index starts at 1)')
	options, args = parser.parse_args()
	if len(args) > 0:
		in_file = args[0]
	else:
		in_file = None
	
	# clean up
	del parser
	
	#############
	# IMPORTANT #
	############################################################################
	# Some of the following MultiSub group separations are due to an unavoidable
	# 100 total group limit amongst all regexes in the MultiSub and some are due
	# to undefined behavior if certain regexes are processed in parallel
	############################################################################
	
	# NOTE: the named group substitutions in the multisubs have to be used instead of
	#       things like (?<=...) b/c of multisub implementation
	symbols1 = MultiSub({
		# replace unicode with ASCII
		r'–|—|−'                         : '-',
		r'’|‘'                           : '\'',
		r'\s*(°|º)\s*C\s*'               : ' DEGREES CELSIUS ',
		r'\s*(°|º)\s*F\s*'               : ' DEGREES FARENHEIT ',
		r'\s*(°|º)\s*'                   : ' DEGREES ',
		r'\s*±\s*'                       : ' PLUS OR MINUS ',
		
		# replace other symbols
		r'\s*#\s*'                       : ' NUMBER ',
		r'\s*&\s*'                       : ' AND ',
		r'\s*%\s*'                       : ' PERCENT ',
		r'\s*=\s*'                       : ' EQUALS ',
		r'\s*\+\s*'                      : ' PLUS ',
		r'\s*<\s*'                       : ' LESS THAN ',
		r'\s*(≤|(<=))\s*'                : ' LESS THAN OR EQUAL TO ',
		r'\s*>\s*'                       : ' GREATER THAN ',
		r'\s*(≥|(>=))\s*'                : ' GREATER THAN OR EQUAL TO ',
		r'(?P<ln1>[A-Z])-(?P<ln2>[0-9])' : '\\g<ln1> \\g<ln2>',
		r'(?P<nl1>[0-9])-(?P<nl2>[A-Z])' : '\\g<nl1> \\g<nl2>',
		r'(?P<ll1>[A-Z])-(?P<ll2>[A-Z])' : '\\g<ll1> \\g<ll2>',
		r'(?P<nn1>[0-9]),(?P<nn2>[0-9])' : '\\g<nn1>\\g<nn2>'
	})
	symbols1.compile()
	symbols2 = MultiSub({
		r'\s*@\s*'                    : ' AT ',
		r'(?P<n1>[0-9])\s*/\s*(?P<n2>[0-9])' : '\\g<n1> OUT OF \\g<n2>',
		r'(?P<l1>[A-Z])\s*/\s*(?P<l2>[A-Z])' : '\\g<l1> OR \\g<l2>',
	})
	symbols2.compile()
	
	blood_pressure = MultiSub({
		r'(?P<bp>B P [0-9]{1,3})\s*/'                       : '\\g<bp> OVER ',
		r'(?P<bpwas>B P WAS [0-9]{1,3})\s*/'                : '\\g<bpwas> OVER ',
		r'(?P<bpis>B P IS [0-9]{1,3})\s*/'                  : '\\g<bpis> OVER ',
		r'(?P<bloodp>BLOOD PRESSURE [0-9]{1,3})\s*/'        : '\\g<bloodp> OVER ',
		r'(?P<bloodpwas>BLOOD PRESSURE WAS [0-9]{1,3})\s*/' : '\\g<bloodpwas> OVER ',
		r'(?P<bloodpis>BLOOD PRESSURE IS [0-9]{1,3})\s*/'   : '\\g<bloodpis> OVER '
	})
	blood_pressure.compile()
	
	wiki = MultiSub({
		# remove wikipedia references
		r'\[[0-9]+\]' : '',
		r'\[EDIT\]'   : ''
	})
	wiki.compile()
	
	# time = MultiSub({
	# 	# replace time of day references
	# 	r'(?<=\s)[0-2]?[0-9]:[0-5][0-9](\s*(AM|PM|A|P)\b)?' : ' <time> '
	# })
	# time.compile()
	
	dates = MultiSub({
		# replace month abbreviations
		r'\bJAN\.'  : ' JANUARY ',   # JAN is also a name
		r'\bFEB\b'  : ' FEBRUARY ',
		r'\bMAR\.'  : ' MARCH ',     # MAR is also a word
		r'\bAPR\b'  : ' APRIL ',
		r'\bJUN\b'  : ' JUNE ',
		r'\bJUL\b'  : ' JULY ',
		r'\bAUG\b'  : ' AUGUST ',
		r'\bSEP\b'  : ' SEPTEMBER ',
		r'\bSEPT\b' : ' SEPTEMBER ',
		r'\bOCT\b'  : ' OCTOBER ',
		r'\bNOV\b'  : ' NOVEMBER ',
		r'\bDEC\b'  : ' DECEMBER ',
		
		# replace weekday abbreviations
		r'\bSUN\.'   : ' SUNDAY ',    # SUN is also a word
		r'\bMON\b'   : ' MONDAY ',
		r'\bTUES\b'  : ' TUESDAY ',
		r'\bWED\.'   : ' WEDNESDAY ', # WED is also a word
		r'\bTHURS\b' : ' THURSDAY ',
		r'\bFRI\b'   : ' FRIDAY ',
		r'\bSAT\.'   : ' SATURDAY '   # SAT is also a word
		
		# replace numerical dates
		# r'[0-9]{1,2}(?P<date_sep>-|/|\\)[0-9]{1,2}(?P=date_sep)[0-9]{2}([0-9]{2})?' : ' <date> ',
	})
	dates.compile()
	
	fractions = MultiSub({
		# replace ¼
		r'(?P<qn>[0-9])¼'  : '\\g<qn> AND A QUARTER ',
		r'(?P<qs>A|1) ¼'   : '\\g<qs> QUARTER ',
		r'(?P<qp>2|3) ¼S?' : '\\g<qp> QUARTERS ',
		r'ONE\s+¼'         : ' ONE\s+QUARTER ',
		r'TWO ¼S?'         : ' TWO QUARTERS ',
		r'THREE ¼S?'       : ' THREE QUARTERS ',
		r'\s*¼S\s*'        : ' QUARTERS ',
		r'\s*¼\s*'         : ' QUARTER ',
		
		# replace ½
		r'(?P<hn>[0-9])½'  : '\\g<hn> AND A HALF ',
		r'\s*½S\s*'        : ' HALVES ',
		r'\s*½\s*'         : ' HALF '
	})
	fractions.compile()
	
	phone_email = MultiSub({
		# delete phONE\s+numbers
		r'(1(-|\.))?((\([0-9]{3}\) ?)|([0-9]{3}(?P<phone_sep>\.|-)))[0-9]{3}(?P=phone_sep)[0-9]{4}' : '',
		
		# delete email addresses
		r'\b[A-Z0-9\._%+\-]+@[A-Z0-9\.\-]+\.[A-Z]{2,4}\b' : ''
	})
	phone_email.compile()
	
	# replace common units of measurement
	units1 = MultiSub({
		r'\s*/\s*GAL\b'             : ' PER GALLON ',
		r'\bGAL\b'                  : ' GALLONS ',
		r'\bLBS\b'                  : ' POUNDS ',
		r'\s*/\s*LB\b'              : ' PER POUND ',
		r'\bLB\b'                   : ' POUND ',
		r'\s*/\s*FL\b'              : ' PER FLUID ',
		r'\bFL\b'                   : ' FLUID ',
		r'\s*/\s*OZ\b'              : ' PER OUNCE ',
		r'\bOZ\b'                   : ' OUNCES ',
		r'\s*/\s*G\b'               : ' PER GRAM ',
		r'(?P<g>[0-9])\s*G\b'       : '\\g<g> GRAMS',
		r'\s*/\s*MCG\b'             : ' PER MICROGRAM ',
		r'\bMCG\b'                  : ' MICROGRAMS ',
		r'\s*/\s*MG\b'              : ' PER MILLIGRAM ',
		r'\bMG\b'                   : ' MILLIGRAMS ',
		r'\s*/\s*KG\b'              : ' PER KILOGRAM ',
		r'\bKG\b'                   : ' KILOGRAMS ',
		r'\s*/\s*PT\b'              : ' PER PINT ',
		r'(?P<pt>[0-9])\s*PT\b'     : '\\g<pt> PINTS ',
		r'\s*/\s*L\b'               : ' PER LITER ',
		r'(?P<l>[0-9])\s*L\b'       : '\\g<l> LITERS ',
		r'\s*/\s*ML\b'              : ' PER MILLILITER ',
		r'\bML\b'                   : ' MILLILITERS ',
		r'\s*/\s*KL\b'              : ' PER KILOLITER ',
		r'\bKL\b'                   : ' KILOLITERS ',
		r'\s*/\s*MM\b'              : ' PER MILLIMETER ',
		r'\bMM\b'                   : ' MILLIMETERS ',
		r'\s*/\s*CM\b'              : ' PER CENTIMETER ',
		r'\bCM\b'                   : ' CENTIMETERS ',
		r'\s*/\s*KM\b'              : ' PER KILOMETER ',
		r'\bKM\b'                   : ' KILOMETERS ',
		r'\s*/\s*M\b'               : ' PER METER ',
		r'(?P<m>[0-9])\s*M\b'       : ' METERS ',
		r'\s*/\s*IN\.'              : ' PER INCH ',
		r'(?P<inches>[0-9])\s*IN\.' : '\\g<inches> INCHES ',
		r'\s*/\s*FT\b'              : ' PER FOOT ',
		r'\bFT\b'                   : ' FEET ',
		r'\s*/\s*YD\b'              : ' PER YARD ',
		r'\bYD\b'                   : ' YARDS ',
		r'\s*/\s*MI\b'              : ' PER MILE ',
		r'\bMI\b'                   : ' MILES ',
		r'\s*/\s*HR\b'              : ' PER HOUR ',
		r'(?P<hr>[0-9])\s*HR\b'     : '\\g<hr> HOURS ',
		r'\s*/\s*MIN\b'             : ' PER MINUTE ',
		r'(?P<min>[0-9])\s*MIN\b'   : '\\g<min> MINUTES ',
		r'\s*/\s*(S|SEC)\b'         : ' PER SECOND ',
		r'(?P<s>[0-9])\s*S\b'       : '\\g<s> SECONDS ',
		r'\bSEC\b'                  : ' SECONDS ',
		r'\s*/\s*HZ\b'              : ' PER HERTZ ',
		r'\bHZ\b'                   : ' HERTZ ',
		r'\s*/\s*V\b'               : ' PER VOLT ',
		r'(?P<v>[0-9])\s*V\b'       : '\\g<v> VOLTS ',
		r'\s*/\s*DBA\b'             : ' PER DECIBEL ',
		r'\bDBA\b'                  : ' DECIBELS ',
		r'\s*/\s*DB\b'              : ' PER DECIBEL ',
		r'\bDB\b'                   : ' DECIBELS ',
		r'\bPPM\b'                  : ' PARTS PER MILLION ',
		r'\bDEGREES F\b'            : ' DEGREES FARENHEIT ',
		r'\bDEGREES C\b'            : ' DEGREES CELSIUS '
	})
	units1.compile()
	units2 = MultiSub({
		r'\bMILLIMETERS\s*²' : ' SQUARE MILLIMETERS ',
		r'\bMILLIMETERS\s*³' : ' CUBIC MILLIMETERS ',
		r'\bMILLIMETER\s*²'  : ' SQUARE MILLIMETER ',
		r'\bMILLIMETER\s*³'  : ' CUBIC MILLIMETER ',
		r'\bCENTIMETERS\s*²' : ' SQUARE CENTIMETERS ',
		r'\bCENTIMETERS\s*³' : ' CUBIC CENTIMETERS ',
		r'\bCENTIMETER\s*²'  : ' SQUARE CENTIMETER ',
		r'\bCENTIMETER\s*³'  : ' CUBIC CENTIMETER ',
		r'\bKILOMETERS\s*²'  : ' SQUARE KILOMETERS ',
		r'\bKILOMETERS\s*³'  : ' CUBIC KILOMETERS ',
		r'\bKILOMETER\s*²'   : ' SQUARE KILOMETER ',
		r'\bKILOMETER\s*³'   : ' CUBIC KILOMETER ',
		r'\bMETERS\s*²'      : ' SQUARE METERS ',
		r'\bMETERS\s*³'      : ' CUBIC METERS ',
		r'\bMETER\s*²'       : ' SQUARE METER ',
		r'\bMETER\s*³'       : ' CUBIC METER ',
		r'\bINCHES\s*²'      : ' SQUARE INCHES ',
		r'\bINCHES\s*³'      : ' CUBIC INCHES ',
		r'\bINCH\s*²'        : ' SQUARE INCH ',
		r'\bINCH\s*³'        : ' CUBIC INCH ',
		r'\bFEET\s*²'        : ' SQUARE FEET ',
		r'\bFEET\s*³'        : ' CUBIC FEET ',
		r'\bFOOT\s*²'        : ' SQUARE FOOT ',
		r'\bFOOT\s*³'        : ' CUBIC FOOT ',
		r'\bMILE\s*²'        : ' SQUARE MILE ',
		r'\bMILE\s*³'        : ' CUBIC MILE ',
		r'\bMILES\s*²'       : ' SQUARE MILES ',
		r'\bMILES\s*³'       : ' CUBIC MILES ',
		r'\bMINUTES\s*²'     : ' MINUTES SQUARED ',
		r'\bMINUTE\s*²'      : ' MINUTE SQUARED ',
		r'\bSECONDS\s*²'     : ' SECONDS SQUARED ',
		r'\bSECOND\s*²'      : ' SECOND SQUARED '
	})
	units2.compile()
	
	# replace military rank abbreviations
	military_rank = MultiSub({
		# air force
		r'\bAMN\b'                 : ' AIRMAN ',
		r'\bA1C\b'                 : ' AIRMAN FIRST CLASS ',
		r'\bSRA\b'                 : ' SENIOR AIRMAN ',
		r'\bSSGT\b'                : ' STAFF SERGEANT ',
		r'\bTSGT\b'                : ' TECHNICAL SERGEANT ',
		r'\bMSGT\b'                : ' MASTER SERGEANT ',
		r'\b1ST ?SGT\b'            : ' FIRST SERGEANT ',
		r'\bSMSGT\b'               : ' SENIOR MASTER SERGEANT ',
		r'\bCMSGT\b'               : ' CHIEF MASTER SERGEANT ',
		r'\bCCMSGT\b'              : ' COMMAND CHIEF MASTER SERGEANT ',
		r'\bCMSAF\b'               : ' CHIEF MASTER SERGEANT OF THE AIR FORCE ',
		r'\b2D ?LT\b'              : ' SECOND LIEUTENANT ',
		r'\b1ST ?LT\b'             : ' FIRST LIEUTENANT ',
		r'\bCAPT\b'                : ' CAPTAIN ',
		r'\bMAJ\b'                 : ' MAJOR ',
		r'\bLTCOL\b'               : ' LIEUTENANT COLONEL ',
		r'\bCOL\b'                 : ' COLONEL ',
		r'\bBRIGGEN\b'             : ' BRIGADIER GENERAL ',
		r'\bMAJGEN\b'              : ' MAJOR GENERAL ',
		r'\bLTGEN\b'               : ' LIEUTENANT GENERAL ',
		r'\bGEN\b'                 : ' GENERAL ',
		
		# army
		r'\bPVT\b'                 : ' PRIVATE ',
		r'\bPV2\b'                 : ' PRIVATE ',
		r'\bPFC\b'                 : ' PRIVATE FIRST CLASS ',
		r'\bSPC\b'                 : ' SPECIALIST ',
		r'\bCPL\b'                 : ' CORPORAL ',
		r'\bSGT\b'                 : ' SERGEANT ',
		r'\bSSG\b'                 : ' STAFF SERGEANT ',
		r'\bSFC\b'                 : ' SERGEANT FIRST CLASS ',
		r'\bMSG\b'                 : ' MASTER SERGEANT ',
		r'\b1SGT\b'                : ' FIRST SERGEANT ',
		r'\bSGM\b'                 : ' SERGEANT MAJOR ',
		r'\bCSM\b'                 : ' COMMAND SERGEANT MAJOR ',
		r'\bSMA\b'                 : ' SERGEANT MAJOR OF THE ARMY ',
		r'\bWO1\b'                 : ' WARRANT OFFICER ',
		r'\bWO2\b'                 : ' CHIEF WARRANT OFFICER TWO ',
		r'\bWO3\b'                 : ' CHIEF WARRANT OFFICER THREE ',
		r'\bWO4\b'                 : ' CHIEF WARRANT OFFICER FOUR ',
		r'\bWO5\b'                 : ' MASTER WARRANT OFFICER FIVE ',
		r'\b2LT\b'                 : ' SECOND LIEUTENANT ',
		r'\b1LT\b'                 : ' FIRST LIEUTENANT ',
		r'\bCPT\b'                 : ' CAPTAIN ',
		# MAJ already handled from air force
		r'\bLTC\b'                 : ' LIEUTENANT COLONEL ',
		# COL already handled from air force
		r'\bBG\b'                  : ' BRIGADIER GENERAL ',
		r'\bMG\b'                  : ' MAJOR GENERAL ',
		r'\bLTG\b'                 : ' LIEUTENANT GENERAL ',
		# GEN already handled from air force
		
		# marine corps
		# PVT already handled
		# PFC already handled
		r'\bLCPL\b'                : ' LANCE CORPORAL ',
		# CPL already handled
		# SGT already handled
		# SSGT already handled
		r'\bGYSGT\b'               : ' GUNNERY SERGEANT ',
		# MSGT already handled
		# 1STSGT already handled
		r'\bMGYSGT\b'              : ' MASTER GUNNERY SERGEANT ',
		r'\bSGTMAJ\b'              : ' SERGEANT MAJOR ',
		r'\bSGTMAJMC\b'            : ' SERGEANT MAJOR OF THE MARINE CORPS ',
		r'\bWO-1\b'                : ' WARRANT OFFICER ',
		r'\bCWO-2\b'               : ' CHIEF WARRANT OFFICER TWO ',
		r'\bCWO-3\b'               : ' CHIEF WARRANT OFFICER THREE ',
		r'\bCWO-4\b'               : ' CHIEF WARRANT OFFICER FOUR ',
		r'\bCWO-5\b'               : ' CHIEF WARRANT OFFICER FIVE ',
		r'\b2NDLT\b'               : ' SECOND LIEUTENANT ',
		r'\b1STLT\b'               : ' FIRST LIEUTENANT ',
		# CAPT already handled
		# MAJ already handled
		# LTCOL already handled
		r'\bBGEN\b'                : ' BRIGADIER GENERAL ',
		# MAJGEN already handled
		# LTGEN already handled
		# GEN already handled
	})
	military_rank.compile()
	
	# replace other common abbreviations
	common_abbrevs = MultiSub({
		# medical
		r'\bB/?P\b'                : ' B P ',
		r'\bDR\b'                  : ' DOCTOR ',
		r'\bW/U\b'                 : ' WORKUP ',
		r'\bPT\b'                  : ' PATIENT ',
		r'\bPTS\b'                 : ' PATIENTS ',
		r'\bDX\b'                  : ' DIAGNOSIS ',
		r'\bRX\b'                  : ' PRESCRIPTION ',
		r'\bTX\b'                  : ' TREATMENT ',
		r'\bY/O\b'                 : ' YEAR OLD ',
		r'(?P<yo>[0-9])\s*YO\b'    : '\\g<yo> YEAR OLD ',
		
		# addresses
		r'\bAPT\b'                 : ' APARTMENT ',
		r'\bRD\b'                  : ' ROAD ',
		r'\bAVE\b'                 : ' AVENUE ',
		r'\bBLVD\b'                : ' BOULEVARD ',
		r'(?P<st>[^0-9])\s+ST\b'   : '\\g<st> STREET ',
		r'(?P<aus>\b(A|AN))\s+US\b': '\\g<aus> U S ',
		r'(?P<nonus>\bNON)\s+US\b' : '\\g<nonus> U S ',
		r'(?P<theus>\bTHE)\s+US\b' : '\\g<theus> U S ',
		r'\bU\.S\.'                : ' U S ',
		
		# names
		r'\bSR\b'                  : ' SENIOR ',
		r'\bJR\b'                  : ' JUNIOR ',
		r'\bMR\b'                  : ' MISTER ',
		r'\bMRS\b'                 : ' MISSES ',
		
		# writing
		r'\bE\.?G\b'               : ' ESTIMATED GUESS ',
		r'\bI\.?E\b'               : ' IN EXAMPLE ',
		r'\bETC\b'                 : ' ETCETERA ',
		
		# general
		r'\bALT\.'                 : ' ALTITUDE ',
		r'\bAPPT\b'                : ' APPOINTMENT ',
		r'\bDEPT\b'                : ' DEPARTMENT ',
		r'\bDIV\b'                 : ' DIVISION ',
		r'\bEST\b'                 : ' ESTABLISHED ',
		r'\bSQ\b'                  : ' SQUARE ',
		r'\bVOL\b'                 : ' VOLUME ',
		r'\bWT\b'                  : ' WEIGHT ',
		r'\bN/A\b'                 : ' NOT APPLICABLE ',
		r'\bW/O\b'                 : ' WITHOUT ',
		r'\bW/(?P<with>[^O])'      : ' WITH \\g<with>',
		r'\bEA\b'                  : ' EACH ',
		r'\bE\b'                   : ' EACH ',
		r'\bO\.?K\b\.?'            : ' OKAY '
	})
	common_abbrevs.compile()
	
	quotes = MultiSub({
		# remove single-quotes, ignoring contractions and MOST
		# cases of possession (doesn't account for cases like jones')
		# don't have to use named group matching here b/c the target substitution is empty
		r'(?<![A-Z])\''          : '',
		r'(?<=[A-Z])\'(?![A-Z])' : ''
	})
	quotes.compile()
	
	# replace written dates
	# sentence = re.sub(r'\b(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)( (([0-2][0-9])|(3[01])|([0-9]))( ?((TH)|(ST)|(ND)|(RD)))?\b)?(,? ([0-9]{2}([0-9]{2})?))?', ' <date> ', sentence)
	
	# note that this is not a completely accurate regex for written numbers,
	# but it is good enough since a completely accurate one is exceedingly
	# long (5035 characters)
	# to see an accurate regex for any written number from 0 up to but not
	# including one billion, in the language_model/scripts directory, run:
	# ./bnf2regex.py ../token_mappers/num_bnf
	# num_words   = '(\b(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN'
	# num_words  += '|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN'
	# num_words  += '|TWENTY|THIRTY|FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY|HUNDRED|THOUSAND|MILLION|BILLION)\b)'
	# eng_num_re  = '((\bA )?' + num_words + ')( (AND )?(A )?' + num_words + '+)*'
	
	# replace each number with its word equivalent
	eras = MultiSub({
		# time eras
		r'20\'?S\b' : ' TWENTIES ',
		r'30\'?S\b' : ' THIRTIES ',
		r'40\'?S\b' : ' FORTIES ',
		r'50\'?S\b' : ' FIFTIES ',
		r'60\'?S\b' : ' SIXTIES ',
		r'70\'?S\b' : ' SEVENTIES ',
		r'80\'?S\b' : ' EIGHTIES ',
		r'90\'?S\b' : ' NINETIES ',
		
		r'(?P<num1>[0-9])-(?P<num2>[0-9])' : '\\g<num1> \\g<num2>'
		
		# digit numbers
		# r'-?(((([1-9][0-9]*|0))?\.[0-9]*)|([1-9][0-9]*)|0)' : ' <num> '
		
		# english number words
		# eng_num_re : ' <num> '
	})
	eras.compile()
	
	num_places = MultiSub({
		r'\bONE\s*ST\b'       : ' FIRST ',
		r'\bTWO\s*ND\b'       : ' SECOND ',
		r'\bTHREE\s*RD\b'     : ' THIRD ',
		r'\bFOUR\s*TH\b'      : ' FOURTH ',
		r'\bFIVE\s*TH\b'      : ' FIFTH ',
		r'\bSIX\s*TH\b'       : ' SIXTH ',
		r'\bSEVEN\s*TH\b'     : ' SEVENTH ',
		r'\bEIGHT\s*TH\b'     : ' EIGHTH ',
		r'\bNINE\s*TH\b'      : ' NINETH ',
		r'\bTEN\s*TH\b'       : ' TENTH ',
		r'\bELEVEN\s*TH\b'    : ' ELEVENTH ',
		r'\bTWELVE\s*TH\b'    : ' TWELFTH ',
		r'\bTHIRTEEN\s*TH\b'  : ' THIRTEENTH ',
		r'\bFOURTEEN\s*TH\b'  : ' FOURTEENTH ',
		r'\bFIFTEEN\s*TH\b'   : ' FIFTEENTH ',
		r'\bSIXTEEN\s*TH\b'   : ' SIXTEENTH ',
		r'\bSEVENTEEN\s*TH\b' : ' SEVENTEENTH ',
		r'\bEIGHTEEN\s*TH\b'  : ' EIGHTEENTH ',
		r'\bNINETEEN\s*TH\b'  : ' NINETEENTH ',
		r'\bTWENTY\s*TH\b'    : ' TWENTIETH ',
		r'\bTHIRTY\s*TH\b'    : ' THIRTIETH ',
		r'\bFORTY\s*TH\b'     : ' FORTIETH ',
		r'\bFIFTY\s*TH\b'     : ' FIFTIETH ',
		r'\bSIXTY\s*TH\b'     : ' SIXTIETH ',
		r'\bSEVENTY\s*TH\b'   : ' SEVENTIETH ',
		r'\bEIGHTY\s*TH\b'    : ' EIGHTIETH ',
		r'\bNINETY\s*TH\b'    : ' NINETIETH ',
		r'\bHUNDRED\s*TH\b'   : ' HUNDREDTH ',
		r'\bTHOUSAND\s*TH\b'  : ' THOUSANDTH ',
	})
	num_places.compile()
	
	too_much_ws     = re.compile(r'[ \t]{2,}')
	all_ws_re       = re.compile(r'^[ \t\r\n]*$')
	num_re          = re.compile(r'-?(((([1-9][0-9]*|0))?\.[0-9]*)|([1-9][0-9]*)|0)')
	money_no_cents  = re.compile(r'\$(?P<num1>[0-9]+)(?!\.[0-9]{2})')
	money           = re.compile(r'\$(?P<num1>[0-9]+)\.(?P<num2>[0-9]{2})')
	space_alpha_num = re.compile(r'((?<=[0-9])(?=[A-Z]))|((?<=[A-Z])(?=[0-9]))') # add a space in between numbers and letters
	
	index = 0
	for sentence in get_sentences(in_file):
		index += 1
		if index < options.start_from:
			continue
		
		# sentence = sentence.strip() # remove leading / trailing whitespace
		sentence = sentence.upper() # capitalize
		
		sentence = symbols1.sub(sentence)
		sentence = money.sub('\g<num1> \g<num2>', sentence)
		sentence = money_no_cents.sub('\g<num1> DOLLARS', sentence)
		sentence = wiki.sub(sentence)
		sentence = dates.sub(sentence)
		sentence = fractions.sub(sentence)
		sentence = phone_email.sub(sentence)
		sentence = space_alpha_num.sub(' ', sentence) # has to be after email (emails can't contain spaces)
		sentence = units1.sub(sentence)
		sentence = units2.sub(sentence)
		sentence = military_rank.sub(sentence)
		sentence = common_abbrevs.sub(sentence)
		sentence = eras.sub(sentence)
		sentence = quotes.sub(sentence)               # has to be after eras (thirties [30's] vs thirty seconds [30s])
		sentence = blood_pressure.sub(sentence)       # has to be after common_abbrevs (b/p)
		sentence = symbols2.sub(sentence)             # has to be after email (@) and blood_pressure ([0-9]/[0-9])
		
		# replace numbers with their english equivalent
		sentence = num_re.sub(num_replace, sentence)
		sentence = num_places.sub(sentence)
		
		# this line removes any characters not in [A-Za-z ]
		sentence = ''.join(i for i in sentence if (ord(i) > 64 and ord(i) < 91) or (ord(i) > 96 and ord(i) < 123) or i == ' ')
		
		if not all_ws_re.match(sentence):
			print too_much_ws.sub(' ', sentence).strip()


def num_replace(match):
	try:
		match = match.string[match.start():match.end()]
		return ' ' + numToText(match).upper() + ' '
	except: # if the number is too large (> 66 digits)
		return ''


def get_sentences(in_file):
	if in_file == None:
		from sys import stdin
		for sentence in stdin:
			yield sentence
	else:
		with open(in_file, 'r') as f:
			for sentence in f:
				yield sentence


if __name__ == '__main__':
	main()
