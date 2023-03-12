import re, collections


def train(text):
	# strip the corpus of punctuation and split it into words
	words = re.findall(r'(?i)[a-z]+\'?[a-z]', text)
	
	# build the model
	model         = collections.defaultdict(lambda: 1)
	previous_word = None
	for current_word in words:
		# unigram frequency
		model[current_word.lower()] += 1
		
		# bigram frequency
		# if previous_word:
		# 	model[previous_word + ' ' + current_word] += 1
		# 	previous_word                              = current_word
	return model


def edits(word):
	alphabet   = 'abcdefghijklmnopqrstuvwxyz\''
	word       = word.lower()
	splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
	deletes    = [a + b[1:] for a, b in splits if b]
	transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
	replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
	inserts    = [a + c + b	 for a, b in splits for c in alphabet]
	return set(deletes + transposes + replaces + inserts)


def known_edits(word, model):
	return set(e2 for e1 in edits(word) for e2 in edits(e1) if e2 in model)


def known(words, model):
	return set(w for w in words if w in model)


def correct(word, model):
	candidates = known([word]) or known(edits(word)) or known_edits(word) or [word]
	all_caps   = re.search(r'[a-z]', word)
	first_caps = re.match(r'[A-Z]')
	best       = max(candidates, key=model.get)
	if all_caps:
		return best.upper()
	if first_caps:
		return best[0].upper() + best[1:]
	return best


if __name__ == '__main__':
	import sys
	model = train(sys.argv[1])
	print correct(sys.argv[2])
