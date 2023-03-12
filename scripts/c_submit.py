#!/usr/bin/env python
import sys
import os
import errno
import subprocess
import argparse
import tempfile
import time
import re

"""
This utility creates and submits a condor job file.

usage: python c_submit.py --help

Known issues: Executables with a " in the filename fail during condor's parsing.
Just don't do it.  Otherwise anything should be supported.

exit codes:
0 - successful
3 - condor error
4 - timeout
other - exit code from command
"""

def condor_submit(command, arguments=[], jobfile=None, errorfile=None, outputfile=None, debug=False, timeout=None, memory=2000):
	#open job file
	jf = None
	if jobfile:
		jf = open(jobfile, 'w')
	else:
		jf = tempfile.NamedTemporaryFile(dir='.')
	
	logfile = jf.name + '.log'
	
	#begin writing job file, starting with always present lines,
	jf.write("""Universe = vanilla
run_as_owner = True
Requirements = Arch =="x86_64"

""")
	jf.write(''.join(('Request_Memory = ', str(memory), '\n')))
	jf.write(''.join(('Log = ', logfile, '\n')))
	
	#condor doesn't support piping both stderr and stdout to the same file
	# so use a wrapper script that combines the streams
	if outputfile == errorfile:
		arguments.insert(0, command)
		command = os.path.join(sys.path[0], 'combine_streams.sh')
		errorfile = None
	
	#write executable
	jf.write(''.join(('Executable = ', command, '\n')))
	
	#start optional lines
	if len(arguments) > 0:
		jf.write('Arguments = "')
		for arg in arguments:
			#escape quotes
			arg = arg.replace('"','""')
			arg = arg.replace("'","''")
			jf.write("'")
			jf.write(arg)
			jf.write("' ")
		jf.write('"\n')
	if errorfile:
		jf.write(''.join(('Error = ', errorfile, '\n')))
	if outputfile:
		jf.write(''.join(('Output = ', outputfile, '\n')))
	
	jf.write('queue\n')
	jf.flush()
	
	#file write now complete
	try:
		#submit job file
		submit = subprocess.Popen(["condor_submit", jf.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		ret = submit.wait()
		out,err = submit.communicate()
		jobnum = out[out.rfind(' ')+1:-2]
		if ret != 0:
			print >> sys.stderr, 'Error submitting condor job, message: ' + err
			sys.exit(3)
		
		#wait for job to finish or timeout
		cwait = ["condor_wait"]
		if timeout:
			cwait.append(['-wait', str(timeout)])
		cwait.append(logfile)
		wait = subprocess.Popen(cwait, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
		
		"""
		This is commented out until I can find a way to quickly check held jobs without polling the master server.
		
		while wait.poll() is None:
			check if job is held in this while statement
			time.sleep(5)
		"""
		
		ret = wait.wait()
		out,err = wait.communicate()
		if ret != 0:
			print >> sys.stderr, 'Job ' + command + ' timed out.'
			sys.exit(4)
		
		#get return code from job
		abnormal = re.compile('(?<=Abnormal termination \(signal )[0-9]+(?=\))')
		normal = re.compile('(?<=Normal termination \(return value )[0-9]+(?=\))')
		ret = 0
		for line in open(logfile):
			m = normal.search(line)
			if m:
				ret = int(m.group(0))
				break
			
			m = abnormal.search(line)
			if m:
				#in linux, terminating signals cause an exit status
				# equal to 128+<signal number>
				ret = 128 + int(m.group(0))
				break
			
		if ret != 0:
			print >> sys.stderr, 'Error in the command ' + command + '.  Check error file for details. return value:\n' + str(ret)
			sys.exit(ret)
	finally:
		#cleanup
		if not debug:
			#ignore file doesn't exist error.
			try:
				os.remove(logfile)
			except OSError, e:
				if e.errno != errno.ENOENT:
					raise
		subprocess.call(["condor_rm", jobnum], stdout = subprocess.PIPE, stderr=subprocess.PIPE)
		jf.close()
		

#main function, only used for parsing command arguments and passing to condor_submit
def main(argv):
	description = 'This is a program that distributes jobs to the cluster using condor.\nThe command will be executed in the current directory, and by default no files will be saved.\nCondor has no knowledge of path variables, so use full or relative paths to executables and files. (for example, do not use ~/, but ../ is fine.)'
	parser = argparse.ArgumentParser(description=description)
	parser.add_argument('command', help='Specify the executable you want to run.')
	parser.add_argument('arguments', nargs=argparse.REMAINDER, help='Any additional arguments after command will be treated as arguments for command.')
	parser.add_argument('--job-file', '-j', type=str, default=None, help ='Specify the job file name.  If not specified, a tempfile will be used and deleted at the end of the job.')
	parser.add_argument('--error-file', '-e', type=str, default=None, help='Specify to make condor capture stderr of command and write it to the file specified.')
	parser.add_argument('--output-file', '-o', type=str, default=None, help='Specify to make condor capture stderr of command and write it to the file specified.')
	parser.add_argument('--debug', '-d', default=False, action='store_true', help='Log files are deleted by default, enable this to keep them for debugging purposes.  Condor logs are stored as <jobfile name>.log')
	parser.add_argument('--timeout', '-t', type=int, default=None, help='Specify a timeout in seconds.')
	parser.add_argument('--memory', '-m', type=int, default=2000, help='Specify amount of memory to request in MB.')
	
	args = parser.parse_args()
	condor_submit(args.command, args.arguments, args.job_file, args.error_file, args.output_file, args.debug, args.timeout, args.memory)

if __name__ == '__main__':
	main(sys.argv)
