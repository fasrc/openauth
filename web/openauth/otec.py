"""
one-time, expiring codes

DESCRIPTION
	Use this module to store codes with expiration dates.  Give users the 
	code, e.g. through email, to be passed back in forms / query strings.  The 
	server can use the code to validate the client.  The "one-time" aspect is 
	up to whatever uses this -- it must call delete() after validating the 
	code; deletion is not combined with isValid() because sometimes the
	flexibility is nice.

REQUIREMENTS
	filesystem:
		make sure OTEC_DIR below exists and is writable by whatever runs this 
		process (e.g. apache)

	uuidgen command

IMPLEMENTATION NOTES
	The filename is the code; the contents are the expiration date.
	
	Codes are based on UUIDs, but can have extra strings prepended to them (the 
	code is the whole thing).
	
	The functions defined in here raise Exceptions when they encounter error 
	conditions (except for mod_python handlers).

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""


import os, time, subprocess

#Something that imports this module may choose to change these values, but of 
#course one must make sure all modules that do so do it consistently.

#OTEC_DIR -- place to store otecs
#The default is in a directory in the calling scripts current working
#directory.
OTEC_DIR = 'otec'

#TIME_FORMAT -- format to use for times stored in the file
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'  #e.g. #2010-04-26 15:40:01

#DEBUG -- boolean for whether or not to include full details in Exceptions and log messages
#WARNING: True may cause tracebacks, shell command output, and other secrets to 
#be included in the Exceptions that are raised.  Only use True in production if 
#your log is secure and you're confident all calling code catches Exceptions.
DEBUG = True


def _code2path(code):
	"""construct the full path to the otec file"""
	return os.path.join(OTEC_DIR, code)

def _tstr2tint(tstring):
	"""convert a string formatted according to TIME_FORMAT to seconds since the epoch (an int)"""
	return int(time.strftime('%s', time.strptime(tstring, TIME_FORMAT)))

def _tint2tstr(tint):
	"""convert seconds since the epoch (an int) to a string formatted according to TIME_FORMAT"""
	return time.strftime(TIME_FORMAT, time.localtime(tint))

def _generateCode(prefix=''):
	"""generate a new, unique code, prepending prefix to it, if given"""
	#python uuid module introduced in 2.5, this is designed to be compatible with 2.4.3 (would use uuid.uuid4() otherwise)
	sh = 'uuidgen -r'
	p = subprocess.Popen(
		sh,
		shell=True,
		stdin=open('/dev/null', 'r'),
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE
	)
	stdout, stderr = p.communicate()
	if p.returncode != 0 or stderr != '':
		if DEBUG:
			msg = "sh code execution [%s] returned non-zero exit status [%s] and/or non-empty stdterr [%s]" % (repr(sh), p.returncode, repr(stderr.strip()))
		else:
			msg = "sh code execution returned non-zero exit status and/or non-empty stdterr"
		raise Exception(msg)
	return '%s%s' % (prefix, stdout.strip())

#---

def new(expiration_date, prefix=''):
	"""create a new otec, expiring at the given date
	
	expires can be an int (seconds since the epoch), or a string (in the format of TIME_FORMAT above); either way, it's stored in the file as a formatted string
	prefix is an optional string to include at the beginning of the code.
	"""
	
	#create the code
	code = _generateCode(prefix)

	#create tstr, the expiration date string to store in the file
	if isinstance(expiration_date, basestring):
		try:
			#make sure it parses
			_tstr2tint(expiration_date)
		except ValueError:
			raise ValueError("string [%s] must be in the time format %s" % (expiration_date, TIME_FORMAT))
		tstr = expiration_date
	elif isinstance(expiration_date, int):
		tstr = _tint2tstr(expiration_date)
	else:
		raise ValueError("invalid type [%s] for expiration_date [%s]" % (type(expiration_date), expiration_date))
	
	try:
		f = open(_code2path(code), 'w')  #the code is in the filename, so the permissions here aren't very important; let the environment determine them
		f.write('%s\n' % tstr)
	finally:
		try:
			f.close()
		except Exception:
			pass
	return code

def isValid(code):
	"""check if a code is valid

	Returns False if it's invalid, doesn't exist, can't be read, etc.
	Does NOT delete the code (i.e. it could be valid again if asked again).
	"""
	#(making this work in 2.4.3, can't combine try+except+finally)
	try:
		try:
			f = open(_code2path(code), 'r')
			data = f.read().strip()
		finally:
			try:
				f.close()
			except Exception:
				pass
	except Exception:
		return False
	
	try:
		expiration_date = _tstr2tint(data)
	except Exception:
		return False
	
	return time.time() < expiration_date

def delete(code):
	"""delete the code from disk, thus invalidating it
	
	If it already doesn't exist, silently return.
	Raises an exception if the file can't be deleted or ensured gone.
	"""
	path = _code2path(code)
	try:
		os.stat(path)
	except OSError, e:
		if hasattr(e, 'errno') and e.errno==2:  #e.g. OSError: [Errno 2] No such file or directory: '/'...
			return
		else:
			raise
	
	os.remove(path)  #let this raise whatever exception it may hit
