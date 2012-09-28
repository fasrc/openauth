"""
basic configuration

DESCRIPTION
	Paremeters controlling how the site functions.
	
	This file is intended to be modified.  See comments below for details on 
	each option.  See the README for a higer-level overview.

REQUIREMENTS
	n/a

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

import os, re

#LOG_FILE -- the absolute path of the log file to use
#The apache user, or whatever user under which the web server is running, must 
#be able to write to it, or create if it does not exist.  This default is to 
#take the name of the directory containing all the psp, html, and the python 
#package, and use that as the name of the log file.
#LOG_FILE = '/var/log/httpd/%s.log' % os.path.basename(os.path.normpath(os.path.join(os.path.dirname(__file__),'..')))
LOG_FILE = '/n/openauth/log/web.log'

#DEBUG -- boolean for whether or not to include full details in Exceptions and log messages
#WARNING: True may cause tracebacks, shell command output, and other secrets to 
#be included in the Exceptions that are raised.  Only use True in production if 
#your log is secure and you're confident all calling code catches Exceptions.
DEBUG = True

#AUTH_TYPE -- what type of authentication to use
#choose one of:
#	'NONE' -- don't require anything
#	'HTTP' -- leave it to apache (i.e. rely on req.user)
#	'FORM' -- present a form to the user (login.psp) and authenticate creds using org.authenticateUser()
#If you choose 'FORM', you must implement org.authenticateUser().  Each psp 
#page must call sessionCheck() in order for this to be respected.  See the 
#README for full details.
AUTH_TYPE = 'FORM'

#RE_VALID_EMAIL_ADDRESS -- filter for allowable email addresses
#This is only applicable if you add code that calls core.sendEmail().  This 
#expression is lax by default, allowing just plain usernames (so that the 
#system emails the account); tighten if desired.  All email addresses are 
#properly quoted/escaped when passed to other programs, regardless of the 
#expression here.
RE_VALID_EMAIL_ADDRESS = re.compile('^[a-zA-Z0-9_\-.+%@]+$')
