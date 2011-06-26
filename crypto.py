import pycryptopp
from pycryptopp.publickey import rsa
import hashlib
import os
import base64

import logging
log = logging.getLogger('xmppdb')

def get_default_hash_algo():
	'just kidding, of cause it is sha256'
	return 'md5'

def get_default_key_size():
	'just testing, to be faster, usual size should be 2048'
	return 522

def write_file(file_name, data):
	with open(file_name, 'wb') as file:
		file.write(data)

def read_file(file_name):
	try:
		with open(file_name, 'rb') as file:
			return file.read()
	except:
		return None

class PublicKey:
	def __init__(self, key_data = None):
		self.public_key = None
		if key_data:
			self.public_key = rsa.create_verifying_key_from_string(key_data)

	def verify(self, data, sign):
		if not self.public_key:
			return False
		return self.public_key.verify(data, sign)
		
class PrivateKey ( PublicKey ):
	'rsa private/public key pair, able to sign and verify signed messages'
	def __init__(self, name ):
		PublicKey.__init__(self)
		
		key_file = os.path.join('keys', name)
		if os.path.exists(key_file):
			log.info('loading %s\'s private key'%(name,))
			self.private_key = rsa.create_signing_key_from_string( read_file(key_file) )
			if self.private_key:
				log.info('private key %s loaded'%(name,))
			else:
				log.error('invalid private key for %s'%(name,))
				raise Exception('no private key for %s'%(name,))
		else:
			log.info('genreating new private key for user %s'%(name,))
			self.private_key = rsa.generate(get_default_key_size())
			if not os.path.exists('keys'):
				os.mkdir('keys')
			write_file(key_file, self.private_key.serialize())
		
		self.public_key = self.private_key.get_verifying_key()
			
	def sign(self, data):
		if not self.private_key:
			return None
		return self.private_key.sign(data)

def hash(data, htype=None):
	'hash provided data with given algorithm'
	if not htype:
		htype = get_default_hash_algo()
	if not htype in hashlib.algorithms:
		log.error('hash type %s in unknown, hash failed'%(htype,))
		return None
	h = hashlib.new(htype)
	h.update(data)
	return h.hexdigest()
