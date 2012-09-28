"""
organization/intrastructure-specific things

DESCRIPTION
	Things commonly involved with what a little website is used for but that 
	involve organization/infrastructure-specific things.  E.g. specific 
	greeting messages, getting user account attributes, the text of error 
	messages, etc.
	
	This file is intended to be modified.

REQUIREMENTS
	Depends on implementation.

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

import os, time, pwd
import config, core


email_from_address = 'rchelp@fas.harvard.edu'

support_email_address = 'rchelp@fas.harvard.edu'


#--- page content and error messages

# general errors

err_str = '<h3><span style="color:red;">ERROR</span></h3>'

def errmsg_general(session, req):
	"""html used for general failures

	Do not include a greeting or other header -- this is used for unexpected errors and may come up after a greeting has already been printed.
	"""
	msg = 'Please email <a href="mailto:%s">%s</a> for futher assistance, noting' % (support_email_address, support_email_address)
	username = core.getUsername(session, req)
	if username is not None:
		msg += ' your username (<em>%s</em>) and' % username
	msg += ' the time this happened (<em>%s</em>).' % time.strftime('%Y-%m-%d %H:%M:%S %Z')
	return """\
%s
<p>
An error occurred while processing your request.
Sorry.
</p>
<p>
%s
</p>
""" % (err_str, msg)

# login page content (only applicable if config.AUTH_TYPE='FORM')

def html_login_intro(session, req):
	"""html presented above the username/password form"""
	return """\
<p>
You must login with your FAS Research Computing username and password.
If you have not yet requested an account, you may do so <a href="http://rc.fas.harvard.edu/request">here</a>.
If you have already requested an account but cannot remember your username and/or password, please contact <a href="mailto:%s">%s</a>.
</p>
<br /><!--(because our paragraph margin-* css is off; remove on other sites)-->
""" % (support_email_address, support_email_address)

def html_login_outro(session, req):
	return """\
"""

def html_login_successful(session, req):
	"""html presented upon successful login when there is no redirect

	Users only see this if they directly hit the login.psp url instead of getting redirected there, since in the latter case they will be redirected to their original request rather than see the page that displays this.
	"""
	base_url_dir = os.path.dirname(req.subprocess_env['SCRIPT_URI'])
	return """\
<p>
Login successful.
</p>
<p>
Please continue <a href="%s">here</a>.
</p>
""" % base_url_dir

def html_login_failed(session, req):
	"""html presented above the username/password form after an authentication attempt has failed."""
	return """
<p>
<span style="color:red;">Login failed.</span>
</p>
"""

def html_logout_successful(session, req):
	"""html presented above the username/password form after an authentication attempt has failed."""
	return """\
<p>
Logout successful.
</p>
"""

def html_logout_link(session, req):
	"""html to use as a logout link
	
	Note that this is not part of any page template by default, you must actively choose to use it.
	"""
	if config.AUTH_TYPE!='FORM': raise Exception("login/logout only makes sense for config.AUTH_TYPE=='FORM'")
	return """\
<a style="float:right;" href="login.psp">logout</a>
<br />
"""


#--- handling users

def getFullName(username):
	"""return the user's full name, or just the username (as given) if that fails
	
	This is provided for convenience only -- it not called anywhere be default, regardless of config.AUTH_TYPE.
	"""
	realname = username
	try: realname = pwd.getpwnam(username)[4]
	except Exception: pass
	if realname=='': realname = username
	return realname

def getEmailAddress(username):
	"""return the email address of the user
	
	This is provided for convenience only -- it not called anywhere be default, regardless of config.AUTH_TYPE.
	"""
	return core.getStdout("/n/sw/rc/bin/username2ldapatts -a mail %s" % core.shQuote(username)).strip()

def authenticateUser(session, req, username, password):
	"""authenticate the username/password combination.
	
	Only used if config.AUTH_TYPE=='FORM'.
	This sets session['username'], iff authentication is successful.
	This should raise an Exception if authentication fails (the caller must make sure to sanitize any error message, since there's no guarantee it won't contain passwords or other sensitive information).
	"""

	if password=='': raise Exception("empty password")  #the ldap bind does not fail for empty password, so must catch it before

	import ldap

	ldap.set_option(ldap.OPT_DEBUG_LEVEL,255)

	try:
		try:
			authenticated = False
			for host in ('dc2-rc', 'dc3-rc'):
				try:
					l = ldap.initialize("ldaps://%s:636/" % host)
					l.protocol_version = ldap.VERSION3
					l.simple_bind_s(
						core.getStdout("/n/sw/rc/bin/username2ldapatts -a distinguishedName %s" % core.shQuote(username)).strip(),
						password
					)  #will raise ldap.INVALID_CREDENTIALS in case of failure
					authenticated = True
					break
				except ldap.SERVER_DOWN, e:
					msg = "got ldap.SERVER_DOWN for [%s]: %s; will retry other hosts if available" % (host, e)
					core.log(msg, session, req)
					continue
			if not authenticated: raise Exception("cannot contact LDAP server(s)")
		except ldap.INVALID_CREDENTIALS:
			raise
	finally:
		try:
			l.unbind_s()
		except Exception:
			pass
