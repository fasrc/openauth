"""
openauth-specific configuration

DESCRIPTION
	Paremeters controlling how openauth functions

	This file is intended to be modified.  See comments below for details on 
	each option.

REQUIREMENTS
	n/a

AUTHOR
	John Brunelle <john_brunelle@harvard.edu>
	Harvard FAS Research Computing
"""

import os

#common parent directory for pretty much everything
ROOT_DIR = '/n/openauth'

#directory containing the google-authenticator binary
#this is prepended to PATH; set it to None if already in the PATH
GABIN    = os.path.join(ROOT_DIR, 'sw', 'google-authenticator', 'usr', 'bin')

#directory containing the qrencode binary
#this is prepended to PATH; set it to None if already in the PATH
QRBIN    = os.path.join(ROOT_DIR, 'sw', 'qrencode', 'bin')

#path to the java jar binary
#this is prepended to PATH; set it to None if already in the PATH
JARBIN   = '/n/sw/jdk1.6.0_23/bin'

#place where all the secrets are to be kept
#in here will be put a directory for each user
SECRETS_ROOT_DIR = os.path.join(ROOT_DIR, 'secrets', 'default')

#the filename to use for the output of the google-authenticator secret generator
SECRET_FILE_BASENAME = 's'

#directory containing the starting contents for the zip of the JAuth client
ZIP_CONTENTS_DIR = os.path.join(ROOT_DIR, 'sw', 'web', 'openauth_zip_starter')

#the client code download has the secret embedded
#this is the placeholder that must be subsituted with the real secret on a per-user basis
SECRET_PLACEHOLDER = 'WVTLMS2BRKCY3X5A'
