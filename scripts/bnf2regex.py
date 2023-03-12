#!/usr/bin/env python
import re
from multisub import MultiSub


# - BNF must reduce to a regular language or behavior is undefined
# - BNF file must follow the format of one rule definition per line
#   with the accepted regex as the last line
# - rule definitions must come before their use
#
# Example BNF file that gives "(bbc)|(de(f?))|g":
# a      ::= b
# rule1  ::= abc
# <rule2>::=de(f?)
# rule3::=g
# rule1|<rule2>|rule3
#
def convert(bnf_file, assignment_operator='::='):
	dictionary = dict()
	accepted   = ''
	with open(bnf_file, 'r') as bnf_file:
		for line in bnf_file:
			line = line.strip()
			if line.find(assignment_operator) > -1: # rule definition
				match     = re.match(r'^\s*(\S+)\s*' + assignment_operator + r'\s*(.+)\s*$', line)
				id, regex = match.groups()
				if len(dictionary) > 0:
					multi_sub = MultiSub(dictionary)
					multi_sub.compile()
					regex = multi_sub.sub(regex)
				dictionary[id] = regex
			else: # accepted regex
				multi_sub = MultiSub(dictionary)
				multi_sub.compile()
				return multi_sub.sub(line)


def main():
	import sys
	print convert(sys.argv[1])


if __name__ == '__main__':
	main()
