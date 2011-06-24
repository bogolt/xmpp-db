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
		pub_msg, pub_msg_sig = self.db.get_message(self.msg_public.id())
		if not pub_msg:
			self.msg_public_selfsign = self.msg_public.sign(self.key, self.msg_public)
			if not self.msg_public_selfsign:
				raise Exception('failed to user\'s sign key')
		
			log.debug('public key message signature %s'%(self.msg_public_selfsign,))
			self.db.add_message(self.msg_public, self.msg_public_selfsign)
			return

		for signature in pub_msg_sig.values():
			if signature.id() == self.msg_public.id():
				self.msg_public_selfsign = signature.copy()
				log.debug('found selfsignature in db %s'%(self.msg_public_selfsign,))
				return
					
	def receive(self, m, sigs):
		'receive - verify, save to db message and signature'
		
		# test message for validity ( hash )
		if not m.is_valid():
			log.error('message %s has inalid hash, dropping it'%(m.id(),))
			#TODO: notify sender that he is bad-bad node
			return
		
		db_msg,db_sigs = self.db.get_message(m.id())
		if not db_msg:
			log.info('message %s not exist in the db, adding it'%(m.id()))
			self.db.add_message(m)
			self.process_signatures(sigs, m.id())
			return True

		log.info('message %s already exist in the db'%(m.id()))
		
		#find new signatures, verify them and add to db
		new_sigs = {}
		for s in sigs.values():
			if not s.id() in db_sigs:
				new_sigs[s.id()] = s
		if not new_sigs:
			log.info('no new signatures avialable for message %s'%(m.id()))
			return True
		
		log.info('%s new signatures available for message %s'%(len(new_sigs), m.id()))
		

	def get_public_key(self, user_id):
		user,_ = self.db.get_message(user_id)
		if not user:
			#TODO: ask other nodes about this user
			return None
		log.info('msg user %s'%(user,))
		return crypto.PublicKey(base64.b64decode( user[message.PUBLIC_KEY]) )
	
	def verify_signature(self, signature, msg_id):
		s = signature.data
		log.debug('verifying signature %s for message %s'%(s, msg_id))
		if not message.ID in s:
			return False
		if not message.SIGNED_MESSAGE in s:
			return False
		if s[message.SIGNED_MESSAGE] != msg_id:
			return False
		if not message.USER in s:
			return False
		#find user
		pubkey = self.get_public_key(s[message.USER])
		if not pubkey:
			log.error('no public key to verify signature %s'%(s,))
			return False
		if not pubkey.verify(msg_id, base64.b64decode(s[message.SIGNATURE])):
			#TODO: tell other user he is bad node, and don't talk to him anymore
			log.error('signature %s is invalid'%(s,))
			return False
		log.info('signature %s is valid'%(s,))
		return True
	
	def process_signatures(self, sign, msg_id):
		valid_signs = {}
		if isinstance(sign, message.Message):
			signs = {sign.id():sign}
		else:
			signs = sign
			
		# Optianally can check first sig existence in the db, and then validiy of unknown sigs
		for s in signs.values():
			if self.verify_signature(s, msg_id):
				valid_signs[s.id()] = s
			
		if valid_signs:
			self.db.add_signatures(valid_signs, msg_id)
	
	def sign(self, msg, more_data = None):
		'sign message with private key'
		msgid = None
		if isinstance(msg, message.Message):
			msgid = msg.id()
		else:
			msgid = msg
		log.info('signing message %s'%(msgid))
		return message.sign_message(msgid, self.key, self.msg_public)
		
	def create_message(self, data):
		msg = message.Message(data)
		log.info('created message %s'%(msg,))
		dbmsg,sign = self.db.get_message(msg.id())
		if dbmsg:
			log.info('message %s already exists in the db'%(dbmsg,))
			return dbmsg,sign
		else:
			log.info('message %s not found in the db'%(msg.id()))
		signature = self.sign(msg)
		log.debug('signed message %s, %s'%(msg.id(), signature))
		
		log.info('adding message %s to db'%(msg.id()))
		self.db.add_message(msg, signature)
		return msg,{signature.id():signature}


montaron = XmppClient('monthy')
m,s = montaron.create_message( {'test':'hey'} )
montaron.receive(m,s)
