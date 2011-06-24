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
			if signature.data[message.USER] == self.msg_public.id():
				self.msg_public_selfsign = signature
				log.debug('found selfsignature in db %s'%(self.msg_public_selfsign,))
				return
		log.error('public key selfsign not found in the db')
		raise('no pubkey selfsign')
					
	def receive(self, m, sigs):
		'receive - verify, save to db message and signature'
		
		# test message for validity ( hash )
		if not m.is_valid():
			log.error('message %s has inalid hash, dropping it'%(m.id(),))
			#TODO: notify sender that he is bad-bad node
			return
		
		log.debug('user %s received message %s, signed with %s'%(self.name, m, sigs))
		
		db_msg,db_sigs = self.db.get_message(m.id())
		if not db_msg:
			log.info('message %s not exist in the db'%(m.id()))
			
			#self.db.add_message(m)
			self.process_signatures(sigs, m)
			#log.info('no known signature found, adding message to unverified table')
				
			return True

		log.info('message %s already exist in the db'%(m.id()))
			
		#find new signatures, verify them and add to db
		new_sigs = {}
		if isinstance(sigs, message.Message):
			if sigs.id() not in db_sigs:
				new_sigs[sigs.id()] = sigs
		else:
			for s in sigs.values():
				if db_sigs and ( not s.id() in db_sigs ):
					new_sigs[s.id()] = s
		if not new_sigs:
			log.info('no new signatures avialable for message %s'%(m.id()))
			return True
		
		log.info('%s new signatures available for message %s'%(len(new_sigs), m.id()))
		self.process_signatures(new_sigs, m)
		

	def get_public_key(self, user_id):
		user,_ = self.db.get_message(user_id)
		if not user:
			#TODO: ask other nodes about this user
			return None
		log.info('found public key %s for user %s'%(user,user_id))
		return crypto.PublicKey(base64.b64decode( user.data[message.PUBLIC_KEY]) )

	def process_signatures(self, sign, msg):
		valid_signs = {}
		unverified_signs = {}
		if isinstance(sign, message.Message):
			signs = {sign.id():sign}
		else:
			signs = sign
			
		for s in signs.values():
			if not s.is_valid():
				log.error('invalid signature hash %s received, throw away'%(s.id(),))
				#TODO: drop connection with bad-bad node who sent this
				continue
			if not message.is_signature_message_valid(s, msg.id()):
				log.error('signature is invalid ( does not contain all necessary fields, or they are invalid )')
				continue
			pubkey = self.get_public_key(s.data[message.USER])
			if not pubkey:
				if msg.id() == s.data[message.USER]:
					log.info('message %s is self-signed with signature %s'%(msg.id(),s.id()))
					#TODO: suppose we always accept Self-Signed messages
					pubkey = crypto.PublicKey(base64.b64decode( msg.data[message.PUBLIC_KEY] ))
					if not pubkey.verify(msg.id(), base64.b64decode(s.data[message.SIGNATURE])):
						log.error('invalid signature %s'%(s.id(),))
						#TODO: invalid signature received
						continue
					log.info('self-signed message %s verified'%(msg.id(),))
					valid_signs[s.id()] = s
					continue
					
				log.info('public key not available to verify signature %s'%(s.id(),))
				#request public key
				unverified_signs[s.id()] = s
				continue
			if not pubkey.verify(msg.id(), base64.b64decode(s[message.SIGNATURE])):
				log.error('invalid signature %s received'%(s.id(),))
				#TODO: sender of this message was trying to lie to us
				continue
			
			log.info('signature %s is verified'%(s.id(),))
			valid_signs[s.id()] = s
			
		if valid_signs:
			log.info('there is %s trusted signatures, adding message %s to db'%(len(valid_signs), msg.id()))
			self.db.add_message(msg, valid_signs)

		if unverified_signs:
			log.info('there is %s unverified signatures'%(len(unverified_signs)))
			#TODO: no point in keeping same message twise ( in differnet tables ). Need a way to keep only signatures instead
			self.db.add_message_unv(msg, unverified_signs)
		
		return True
	
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


xzar = XmppClient('xzar')
xzar.receive(montaron.msg_public, montaron.msg_public_selfsign)
