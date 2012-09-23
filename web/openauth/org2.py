"""
helpers for getting personnel-related information and any other miscellaneous organization-specific things

DESCRIPTION
	This is all the openauth organization-specific greeting/error messages and 
	helper functions factored out of other code.

	This file is intended to be modified.

REQUIREMENTS
	A way to...
	
	- convert usernames to full names
	
	- get an email address for a username

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

from lilpsp import config, core, org
import os



#--- secret key customization

def getSecretKeyLabel(username):
	"""return the label used for the secret key
	
	This is part of what's encoded in the QR code, and it's the identifier used by most clients.
	"""
	return '%s@login.rc.fas.harvard.edu' % username



#--- misc messages


def greeting(session, req):
	"""html used at the very top of pages"""
	greeting = "Hello"
	username = core.getUsername(session, req)
	if username is not None: greeting += " %s" % org.getFullName(username)
	msg = """\
<p>
%s,
</p>
<br /><!--(because our paragraph margin-* css is off; remove on other sites)-->
""" % greeting
	if config.AUTH_TYPE=='HTTP':
		msg += """\
<p>
<small>(If you are not %s, you must close your browser and restart.)</small>
</p>
<br /><!--(because our paragraph margin-* css is off; remove on other sites)-->
""" % (fullname)
	return msg


def intro(session, req):
	"""html used between the greeting and the explanation to wait for the email with the continuation link"""
	return """\
<p>
Welcome to the FAS Research Computing openauth configuration page.
This is how you get setup to use 2-factor authentication in order to access the RC VPN, the Odyssey cluster, and other RC resources.
This is also how you configure an additional device for access.
</p>"""


def extra_info_on_time_skew(session, req):
	"""html to add after the note about the importance of time sync (e.g. a link to a FAQ item)"""
	return """See <a href="http://rc.fas.harvard.edu/kb/openauth/troubleshooting">here</a> for more information."""


def outro(session, req):
	"""html used at the bottom of the last page in the process"""
	return """Please see <a href="http://rc.fas.harvard.edu/openauth/">http://rc.fas.harvard.edu/openauth/</a> for the names of the new servers to use for vpn and ssh access to Research Computing servers, plus links to our Knowledge Base for troubleshooting."""



#--- email contents


def otec_email_subject(session, req):
	"""subject of the continuation link email"""
	return "Harvard FAS Research Computing openauth continuation link"


def otec_email_body_header(session, req):
	"""text to use at the top of the continuation link email body (before the link)"""
	username = req.user.lower()
	fullname = org.getFullName(username)
	return """\
Hello %s,

Please use the following link to continue with your Research Computing openauth configuration:""" % (fullname,)


def otec_email_body_footer(session, req):
	"""text to use at the bottom of the continuation link email body (after the link)"""
	return """\
Thank you,

FAS Sciences Division Research Computing
rchelp@fas.harvard.edu
http://rc.fas.harvard.edu/"""



#--- error messages


def errmsg_no_email(session, req):
	"""html error message when email address lookup fails"""
	msg = 'Please contact <a href="mailto:%s">%s</a> and provide us with your email address' % (org.support_email_address, org.support_email_address)
	username = core.getUsername(session, req)
	if username is not None:
		msg += ' and username (<code>%s</code>)' % username
	msg += "."
	return """\
%s
<p>
Research Computing has no email address for you on file.
You must have a valid email address in order to continue with this process.
%s
</p>
""" % (greeting(session, req), msg)


def errmsg_bad_otec(session, req):
	"""html error message when continuation link verification fails"""
	req.add_common_vars()
	base_url_dir = os.path.dirname(req.subprocess_env['SCRIPT_URI'])  #e.g. 'https://SERVER/PATH/'
	return """\
%s
<p>
The link you are using has expired or is not valid.
</p>
<p>
Please go to <a href="%s">%s</a> to start over.
</p>
""" % (org.err_str, base_url_dir, base_url_dir)
