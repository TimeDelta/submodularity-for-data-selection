import signal


class TimeoutException(Exception): 
	pass


class timeout:
	def __init__(self, time):
		self.time = time
	
	def __enter__(self):
		self.old_handler = timeoutIn(self.time)
	
	def __exit__(self, type, value, traceback):
		resetTimeoutHandler(self.old_handler)


def timeoutDecorator(time, default):
	def timeoutFunction(f):
		def f2(*args):
			old_handler = timeoutIn(time)
			try: 
				return_value = f(*args)
			except TimeoutException:
				return default
			finally:
				resetTimeoutHandler(old_handler)
			cancelTimeout()
			return return_value
		return f2
	return timeoutFunction


def timeoutHandler(signum, frame):
	raise TimeoutException("An operation timed out.")


def timeoutIn(seconds):
	# define what to do in the event of an alarm
	old_handler = signal.signal(signal.SIGALRM, timeoutHandler)
	
	# triger alarm in specified number of seconds
	signal.alarm(seconds)
	return old_handler


def cancelTimeout():
	signal.alarm(0)


def resetTimeoutHandler(handler):
	signal.signal(signal.SIGALRM, handler)
