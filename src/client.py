#!/usr/bin/python
import crypto
import logging
import base64
import message
import db

log = logging.getLogger('xmppdb')

h = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
h.setFormatter(formatter)
log.addHandler(h)
log.setLevel(logging.DEBUG)

class XmppClient:
	def __init__(self, name):
		log.info('initializing client %s'%(name,))
		self.name = name
		self.db = db.Db(name)
		self.key = crypto.PrivateKey(name)
		self.make_public()
			
	def make_public(self):
		'prepare public key and self-sign it'
				
		self.msg_public = message.generate_public_key_message(self.key)
		log.debug('public key message %s'%(self.msg_public,))
		if not self.msg_public:
			raise Exeption('failed to generate public key message')
		
		# first try to get the key from the db
		pub_msg = self.db.get_message(self.msg_public.id())
		if not pub_msg:
			self.msg_public_selfsign = self.msg_public.sign(self.key, self.msg_public)
			if not self.msg_public_selfsign:
				raise Exception('failed to user\'s sign key')
		
			log.debug('public key message signature %s'%(self.msg_public_selfsign,))
			self.db.add_message(self.msg_public, self.msg_public_selfsign)
		else:
			_,self.msg_public_signs = self.db.get_message(self.msg_public.id())
			for signature in self.msg_public_signs.values():
				if signature[message.USER] == self.msg_public.id():
					self.msg_public_selfsign = signature.copy()
					log.debug('found selfsignature in db %s'%(self.msg_public_selfsign,))
					break
					
	def received(self, msg, sigs):
		pass
	
	def create(self, data):
		'create new message and sign it'
		
	def sign(self, message_id, more_data = None):
		'sign message with private key'
		log.info('signing message %s'%(message_id))
		s = {'message':message_id, 'type':'signature'}
		if more_data:
			s.update(more_data)
		s['signature'] = base64.b64encode( self.private_key.sign(message_id) )
		s['user'] = self.public_id['id']
		return s
		
	def create_message(self, message):
		msg = hash_message(message)
		signature = hash_message(self.sign(msg['id']))
		msg['signatures']={signature['id']:signature}
		log.info('generated and signed message %s'%(msg,))
		return msg


montaron = XmppClient('monthy')
