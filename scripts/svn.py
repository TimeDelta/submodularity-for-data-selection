import os

def currentRevision():
	return int(os.popen("svn info | grep 'Revision' | awk '{print $2}'").read())
