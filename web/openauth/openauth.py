"""
administering google-authenticator two-factor authentication

DESCRIPTION
	This handles creating, reading, and deleting secrets file; encoding the 
	secrets in QR code images; etc.
	
	Note that importing this module might add some things to PATH.

REQUIREMENTS
	See the main website for the latest instructions and requirements.
	Currently, the reqirement are mainly:

	filesystem layout
		The directories named in config2.py must exist, be readable by whatever 
		calls this, and in some cases writable, too.
	
	google-authenticator program for generating secrets
	
	qrencode package

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

from lilpsp import config, core
import config2, org2
import os, errno, tempfile


#--- misc prep

if config2.GABIN is not None:
	os.environ['PATH'] = '%s:%s' % (config2.GABIN, os.environ['PATH'])
if config2.QRBIN is not None and config2.QRBIN != config2.GABIN:
	os.environ['PATH'] = '%s:%s' % (config2.QRBIN, os.environ['PATH'])
if config2.JARBIN is not None and (config2.JARBIN != config2.GABIN and config2.JARBIN != config2.QRBIN):
	os.environ['PATH'] = '%s:%s' % (config2.JARBIN, os.environ['PATH'])


#--- internal helpers

def _getSecretDir(username):
	"""return the full path to the directory in which to store the secret file (regardless of whether or not it exists)"""
	return os.path.join(config2.SECRETS_ROOT_DIR, username)

def _getSecretFilename(username):
	"""return the full path to the secret file (regardless of whether or not it exists)"""
	return os.path.join(_getSecretDir(username), config2.SECRET_FILE_BASENAME)

def _makeSecretDir(username):
	"""create the user's directory if it does not already exist; return its full path"""
	dirname = _getSecretDir(username)
	#(most use cases will be creating it anew, so assume that as the default action)
	try:
		os.makedirs(dirname, 0770)  #(umask is still applied)
	except OSError, e:
		if e.errno != errno.EEXIST: raise  #(we're implementing mkdir -p)
	return dirname

def _deleteSecretDir(username):
	"""attempt to delete the directory; raise an Exception upon failure, including if it's not empty"""
	os.rmdir(_getSecretDir(username))

def _QRCode(data):
	"""encode data as QR Code png image
	
	This returns the bytes; there is no file stored on disk.
	"""
	sh = 'qrencode -o - -s 6 %s' % core.shQuote(data)
	return core.getStdout(sh)


#--- main methods

def secretFileExists(username):
	"""boolean of whether or not the secret for the user already exists"""
	return os.path.exists(_getSecretFilename(username))

def makeSecretFile(username):
	"""create the secret for the user
	
	This will overwrite the secret if it already exists (that's the behavior of google-authenticator itself).
	"""
	sdir = _makeSecretDir(username)
	##old version had no command-line options, the below accomplishes a custom --secret with hack of $HOME -> $SDIR and manually changing the hard-coded filename
	#sh = "echo -e 'y\nn\nn\nn' | SDIR='%s' '%s/google-authenticator'" % (sdir, config2.GABIN)
	sh = "google-authenticator --secret=%s/s --time-based --force --disallow-reuse --window-size=5 --no-rate-limit" % core.shQuote(sdir)
	return core.getStdout(sh)

def deleteSecretFile(username):
	"""delete the secret belonging to the user
	
	This does nothing if the file doesn't exist.
	This also tries to remove the directory for the user; any failure to remove the directory (including if it's not empty) is ignored.
	"""
	if secretFileExists(username):
		os.remove(_getSecretFilename(username))  #(let it raise any exception)
	try:
		os.rmdir(_deleteSecretDir(username))
	except Exception:  #(including OSError: [Errno 39] Directory not empty: '...')
		pass

def getSecret(username):
	"""get the secret (the 16-character string) belonging to the user"""
	try:
		f = open(_getSecretFilename(username))
		for line in f:
			return line.strip()  #the first line is the secret
	finally:
		try:
			f.close()
		except Exception:
			pass

def getQRCodeBytes(username):
	"""get the bytes of a QR Code png containing the secret belonging to the user"""
	data = 'otpauth://totp/%s?secret=%s' % (org2.getSecretKeyLabel(username), getSecret(username))
	return _QRCode(data)

def getZipBytes(username):
	"""get the bytes of the zip file with the JAuth client, customized to the user (secret is embedded)"""
	tmpd = tempfile.mkdtemp(dir='/tmp')
	try:
		zipdbasename = '%s-openauth' % username
		zipdpath = os.path.join(tmpd, zipdbasename)
		
		sh = "rsync -a %s/ %s/" % (core.shQuote(config2.ZIP_CONTENTS_DIR), core.shQuote(zipdpath))
		core.getStdout(sh)
		
		f = open(os.path.join(zipdpath, 'AuthenticatorGUI.class'),'r')
		classbytes = f.read()
		f.close()
		classbytes = classbytes.replace(config2.SECRET_PLACEHOLDER, getSecret(username),1)
		f = open(os.path.join(zipdpath, 'AuthenticatorGUI.class'),'w')
		f.write(classbytes)
		f.close()

		sh = "cd %s && jar uf JAuth.jar AuthenticatorGUI.class && rm AuthenticatorGUI.class" % core.shQuote(zipdpath)
		core.getStdout(sh)
		sh = "cd %s && mv openauth.sh %s-openauth.sh && mv openauth.bat %s-openauth.bat && cd .. && zip -r %s.zip %s" % (core.shQuote(zipdpath), core.shQuote(username), core.shQuote(username), core.shQuote(zipdbasename), core.shQuote(zipdbasename))
		core.getStdout(sh)
		f = open(os.path.join(tmpd, '%s.zip' % zipdbasename),'r')
		bytes = f.read()
		f.close()
		return bytes
	finally:
		try:
			if tmpd.startswith('/tmp'):
				sh = "rm -fr /tmp/%s" % core.shQuote(tmpd[len('/tmp/'):])
				core.getStdout(sh)
		except Exception:
			pass


#--- handlers (since they're directly called by apache, they should handle all exceptions, too)

def downloadHandler(req):
	"""otec protection for, and customization of, file downloads, i.e. dynamic non-html content"""


	#--- BEGIN TEMPLATE CODE...

	try:
		from mod_python import apache, util, Session
		
		session = Session.Session(req)
		form = util.FieldStorage(req, keep_blank_values=1)

		req.add_common_vars()
		
		base_url_dir = os.path.dirname(req.subprocess_env['SCRIPT_URI'])  #e.g. 'https://SERVER/PATH/'
		base_fs_dir  = os.path.dirname(req.subprocess_env['SCRIPT_FILENAME'])
		
		msg = "request from ip [%s] from user [%s]" % (req.subprocess_env['REMOTE_ADDR'], core.getUsername(session, req))
		core.log(msg, session, req)
		
		core.sessionCheck(session, req)

		#--- ...END TEMPLATE CODE
		
		
		import otec

		#reset otec defaults; make sure this is in sync with index.psp, else import order will matter
		otec.OTEC_DIR = os.path.join(config2.ROOT_DIR, 'otec')
		otec.DEBUG = config.DEBUG

		username = core.getUsername(session, req)
		if username is None:
			raise Exception("internal error: openauth must be behind some compatible authentication wall")
		
		#check the otec
		code = None
		try:
			code = form['otec']
		except KeyError:
			pass
		if code is None or not otec.isValid(code) or not code.startswith(username):
			msg = "expired, invalid, or unprovided otec for user [%s]: %s" % (username, code)
			core.log(msg, session, req)
			req.internal_redirect(os.path.join(base_url_dir, 'fail_otec.psp'))
			return apache.OK
				
		msg = "accepted otec [%s] for user [%s]" % (code, username)
		core.log(msg, session, req)
		
		#detemine what file to serve up
		try:
			f = os.path.basename(req.uri)
			if f not in ('qrcode.png', '%s-openauth.zip' % username): raise BreakOut
		except (KeyError, BreakOut):
			msg = "unexpected download [%s] by user [%s]" % (f, username)
			core.log(msg, session, req)
			req.internal_redirect(os.path.join(base_url_dir, 'fail_general.psp'))
			return apache.OK
		
		#handle feeding out the bytes
		if   f=='qrcode.png':
			bytes = getQRCodeBytes(username)
			req.headers_out.add('Pragma', 'no-cache')
			req.headers_out.add('Content-Type', 'image/png')
			req.write(bytes)
		elif f==('%s-openauth.zip' % username):
			bytes = getZipBytes(username)
			req.headers_out.add('Content-Disposition', 'attachment; filename="%s"' % f)
			req.headers_out.add('Content-Type'       , 'application/zip')
			req.write(bytes)
		
		#delete the otec
		try:
			otec.delete(code)
			msg = "deleted otec [%s] for user [%s]" % (code, username)
			core.log(msg, session, req)
		except Exception, e:
			msg = "ERROR: failed to delete otec [%s] for user [%s]: %s" % (code, username, e)
			core.log(msg, session, req, e)
			pass  #everything else worked, and the user is good to go; the otec will expire anyways


		#--- BEGIN TEMPLATE CODE...
		
		return apache.OK
	except apache.SERVER_RETURN:
		##if it's re-raised, sessions start over; passing seems wrong but it's the only way I know of to make sessions persist across redirect
		#raise
		pass
	except Exception, e:
		if not ( 'session' in globals() and 'core' in globals() and 'base_url_dir' in globals() ):
			raise  #just bailout and let the server handle it (if configured with PythonDebug On, the traceback will be shown to the user)
		else:
			msg = "ERROR: uncaught exception when handling user [%s]: %s" % (core.getUsername(session, req), e)
			core.log(msg, session, req, e)
			req.internal_redirect(os.path.join(base_url_dir, '..', 'fail_general.psp'))
			return apache.OK  #(not sure if this does anything)
	
	#--- ...END TEMPLATE CODE
