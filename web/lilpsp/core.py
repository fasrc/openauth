"""
generic functionality

DESCRIPTION
	Generic functionality like logging, session handling, etc., plus utilities 
	for sending email, executing shell code, etc.
	
	This file is not intended to be modified.

REQUIREMENTS
	mail command line program, if using sendMail().

	uuencode, if using sendEmail() to sent attachments.

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

import sys, os, time, subprocess, urllib, traceback
from mod_python import util, apache
import config


#--- sanity checks

if config.AUTH_TYPE not in ('NONE', 'HTTP', 'FORM'): raise Exception("unknown config.AUTH_TYPE [%s]" % config.AUTH_TYPE)


#--- basic stuff

def log(msg, session=None, req=None, e=None):
	"""write the given message to the log file
	
	session, if given, should be an apache session object; this will use it to add info to the message.
	req, if given, should be an apache request object; this will use it to add info to the message.
	e, if given, should be an Exception object; this will use it and the current exception stack to add info to the message.
	This should never raise an Exception.
	"""
	#should never raise an exception
	try:
		if session is not None:
			sessionid = session.id()
		else:
			sessionid = 'n/a'
		if req is not None:
			path = req.uri
		else:
			path = 'n/a'
		prefix = "%s: %s: %s: " % (time.strftime('%Y-%m-%d %H:%M:%S'), sessionid, path)
		if config.DEBUG and e is not None:
			tbstr = ''.join(traceback.format_exception(*sys.exc_info())).strip()
			for line in tbstr.split('\n'):
				open(config.LOG_FILE, 'a').write("%sDEBUG: %s\n" % (prefix, line))
		open(config.LOG_FILE, 'a').write("%s%s\n" % (prefix, msg))
	except Exception:
		pass


#--- sessions/auth

#Session management is done with mod_python's session object (http://www.modpython.org/live/current/doc-html/pyapi-sess.html).
#The default session timeout is 30 minutes.
#For config.AUTH_TYPE=='FORM', the presence of session['username'] implies there has been successful authentication, but always use getUsername() instead.

def sessionCheck(session, req):
	"""ensure the session is valid

	What this does depends on config.AUTH_TYPE.
	For config.AUTH_TYPE=='NONE', do nothing.
	For config.AUTH_TYPE=='HTTP', raise an exception if req.user is None.
	For config.AUTH_TYPE=='FORM', if user is not logged in, redirect to a login page (the login page should redirect back to the caller's url).
	Due to the latter case, this must be called before any output is written to the client.
	"""
	log("sessionCheck called", session, req)
	if config.AUTH_TYPE=='NONE':
		log("sessionCheck passed", session, req)
		pass
	elif config.AUTH_TYPE=='HTTP':
		if req.user is None:
			log("sessionCheck failed", session, req)
			raise Exception("HTTP authentication misconfiguration (req.user is None)")
		else:
			log("sessionCheck passed", session, req)
	elif config.AUTH_TYPE=='FORM':
		if session.is_new() or not session.has_key('username'):
			log("sessionCheck failed", session, req)
			try:
				util.redirect(req, 'login.psp?redirect=%s' % urllib.quote_plus(req.unparsed_uri))
			except apache.SERVER_RETURN:  #fix for pre-3.3.1 bug where it uses apache.OK instead of apache.DONE (https://issues.apache.org/jira/browse/MODPYTHON-140)
				raise apache.SERVER_RETURN, apache.DONE
		else:
			log("sessionCheck passed", session, req)
	else:
		raise Exception("sanity check")

def getUsername(session, req):
	"""return the username, or None if not applicable or not yet authenticated.
	
	Should only be called after sessionCheck().
	"""
	if config.AUTH_TYPE=='NONE':
		return None
	elif config.AUTH_TYPE=='HTTP':
		return req.user.lower()  #(may be None)
	elif config.AUTH_TYPE=='FORM':
		try:
			return session['username']
		except KeyError:
			return None
	else:
		raise Exception("sanity check")


#--- handling shell code calls

def errorCheck(sh, returncode, stderr):
	"""raise an Exception if shell code status and/or stderr indicate an error"""
	if returncode!=0 or stderr!='':
		if config.DEBUG:
			msg = "sh code execution [%s] returned non-zero exit status [%s] and/or non-empty stdterr [%s]" % (repr(sh), returncode, repr(stderr.strip()))
		else:
			msg = "sh code execution returned non-zero exit status and/or non-empty stdterr"
		raise Exception(msg)

def shQuote(text):
	"""quote the given text so that it is a single, safe string in sh code.

	Note that this leaves literal newlines alone (sh and bash are fine with that, but other tools may mess them up and need to do some special handling on the output of this function).
	"""
	return "'%s'" % text.replace("'", r"'\''")

def getStdout(sh, check=True):
	"""execute the given sh code and return stdout (a string)
	
	If check is True, raise an Exception for non-zero returncode or non-empty stderr.
	Note that stdout is not stripped of any trailing newlines.
	"""
	p = subprocess.Popen(
		sh,
		shell=True,
		stdin=open('/dev/null', 'r'),
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE
	)
	stdout, stderr = p.communicate()
	if check: errorCheck(sh, p.returncode, stderr)
	return stdout


#--- email

def sendEmail(toEmailAddress, subject, body=None, fromEmailAddress=None, attachmentFilename=None, attachmentDisplayName=None):
	"""send an email
	
	toEmailAddress can be a string (single email address) or list of strings (each a single email address).
	If attachmentDisplayName is not None, use a different name for the attachment, else use the basename of the given attachmentFilename.
	Having both a body and an attachment is currently not supported.
	"""
	if isinstance(toEmailAddress, basestring):
		if not config.RE_VALID_EMAIL_ADDRESS.match(toEmailAddress): raise Exception("[%s] is not a valid email address" % toEmailAddress)
		toargs = shQuote(toEmailAddress)
	elif isinstance(toEmailAddress, list):
		for x in toEmailAddress:
			if not config.RE_VALID_EMAIL_ADDRESS.match(x): raise Exception("[%s] is not a valid email address" % x)
		toargs = ' '.join([ shQuote(x) for x in toEmailAddress ])
	else:
		raise TypeError("[%s] is not a string or list" % toEmailAddress)
	
	if fromEmailAddress is None:
		fromargs = ''
	else:
		if not config.RE_VALID_EMAIL_ADDRESS.match(fromEmailAddress): raise Exception("[%s] is not a valid email address" % fromEmailAddress)
		fromargs = '-- -r %s' % shQuote(fromEmailAddress)

	if attachmentFilename is not None:
		if body is not None: raise Exception("sending an attachment along with a message body is not supported")

		if attachmentDisplayName is None: attachmentDisplayName = os.path.basename(attachmentFilename)
		if "'" in attachmentFilename   : raise Exception("malformed, dangerous input")
		if "'" in attachmentDisplayName: raise Exception("malformed, dangerous input")
		
		sh = "uuencode %s %s | mail -s %s %s %s" % (shQuote(attachmentFilename), shQuote(attachmentDisplayName), shQuote(subject), toargs, fromargs)
		p = subprocess.Popen(
			sh,
			shell=True,
			stdin=open('/dev/null', 'r'),
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		stdout, stderr = p.communicate()
	else:
		sh = "mail -s %s %s %s" % (shQuote(subject), toargs, fromargs)
		p = subprocess.Popen(
			sh,
			shell=True,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE
		)
		stdout, stderr = p.communicate(input=body)
	
	#when mail fails, status is zero and stderr is empty; stdout has the error; e.g. "Insufficient disk space; try again later"...
	if p.returncode!=0 or stdout.strip()!='' or stderr.strip()!='':
		if config.DEBUG:
			msg = "sh code execution [%s] returned non-zero exit status [%s] and/or non-empty stdout [%s] (mail command reports errors there) and/or non-empty stdterr [%s]" % (repr(sh), p.returncode, repr(stdout.strip()), repr(stderr.strip()))
		else:
			msg = "sh code execution returned non-zero exit status and/or non-empty stdout (mail command reports errors there) and/or non-empty stdterr"
		raise Exception(msg)
