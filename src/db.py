import pymongo
import message
import logging
log = logging.getLogger('xmppdb')

class Db:
	def __init__(self, name):
		self.conn = pymongo.Connection()
		self.db = self.conn['xmppdb_%s'%(name.replace('.','_'),)]

		# message signed with valid signatures
		self.message = self.db.message
		self.signature = self.db.signature
		
		# signatures which does not have public key ( yet )
		self.unverified_signature = self.db.unverified_signature
		
		# message without verified signatures
		self.unverified_message = self.db.unverified_message
		
		#log.info('Debug - remove all entries before use')
		self.debug_clear()
		
		self.unverified_signature.remove()
		self.unverified_message.remove()
		
		self.show()
		
		#recent messages
		self.recent = []

	def debug_clear(self):
		self.message.remove()
		self.signature.remove()
		
	def show(self):
		log.info('db status')
		for msg in self.message.find():
			log.info('msg %s'%(msg,))
	
	def exists(self, id):
		return None != self.get_message(id)
	
	def get_message_unv(self, id):
		'get message from list of unverified messages'
		msg = self.unverified_message.find_one({'id':id})
		if not msg:
			return None
		m = msg.copy()
		del msg['_id']
		return message.Message(m)
	
	def get_signatures(self, id):
		'get signatures for msg id specified'
		sigs = {}
		for sig in self.signature.find({message.SIGNED_MESSAGE:id}):
			del sig['_id']
			sigs[sig[message.ID]] = message.Message(sig)
		return sigs
	
	def get_messages(self, type, value):
		msgs = self.message.find({type:value})	
		msg_list = []
		for m in msgs:
			del m['_id']
			if message.TYPE in m:
				del m[message.TYPE]
			msg_list.append( (m.copy(), self.get_signatures(m[message.ID])) )
		return msg_list
	
	def get_message_from_table(self, id, is_verified):
		'get message from given table - eighter save or not'
		
		msg_table = self.message
		sig_table = self.signature
		if not is_verified:
			msg_table = self.unverified_message
			sig_table = self.unverified_signature
			
		msg = msg_table.find_one({message.ID:id})
		if not msg:
			return None, None
		log.debug('db message found %s'%(msg,))
		m = msg.copy()
		del m['_id']
		if message.TYPE in m:
			del m[message.TYPE]
		
		sigs = {}
		for sig in sig_table.find({message.SIGNED_MESSAGE:id}):
			del sig['_id']
			sigs[sig[message.ID]] = message.Message(sig)
		
		return message.Message(m),sigs
		
	def add_message_to_table(self, msg, sigs, is_verified):
		'add message to table, consider there is no such message yet'
		#there is no point in adding existing message, so no verification is done
		#to add signatures to an existing message, use add_signatures
		
		log.info('adding to db msg %s'%msg.data[message.ID])
		
		msg_table = self.message
		if not is_verified:
			msg_table = self.unverified_message
		
		log.debug('db insert message %s'%(msg.id()))
		
		m = msg.data.copy()
		if message.PUBLIC_KEY in m:
			m[message.TYPE] = message.PUBLIC_KEY
		elif message.JID in m:
			m[message.TYPE] = message.JID
			
		msg_db = msg_table.find_one({message.ID:msg.id()})
		if msg_db:
			return None
		
		self.recent.append(msg)
		msg_table.insert(m)
		
		if sigs:
			self.add_signature_to_table(sigs, is_verified)
	
	def get_recent(self):
		'recently received ( signed ) messages'
		r = []
		r,self.recent = self.recent,r
		return r
	
	def add_signature_to_table(self, sigs, is_verified):
		'add more signatures to an existing message'

		if not sigs:
			return None
		
		sig_table = self.signature
		if not is_verified:
			sig_table = self.unverified_signature
			
		if isinstance(sigs, message.Message):
			log.debug('db insert message signature %s'%(sigs.id()))
			sig_table.insert(sigs.data.copy())
		else:
			for s in sigs.values():
				log.debug('db insert message signature %s'%(s.id()))
				sig_table.insert(s.data.copy())
	
	def get_friends(self):
		return self.get_messages(message.TYPE, message.JID)
		
	def get_message(self, id):
		'get verified and signed message with its signature if available'
		return self.get_message_from_table(id, True)
	
	def add_message(self, msg, signature = None):
		'no verification requied, considered message is yet unknown'
		return self.add_message_to_table(msg, signature, True)

	def add_message_unv(self, msg, signature = None):
		'no verification requied, considered message is yet unknown'
		return self.add_message_to_table(msg, signature, False)
	
	def add_signatures(self, sigs_dict):
		'add dict of signatures for one single message'
		return self.add_signature_to_table(sigs_dict, True)

	def get_unverified_signatures(self, user_id):
		'find all unverified messages, signed with given user'
		sigs = {}
		for m in self.unverified_signature.find({message.USER:user_id}):
			del m['_id']
			sigs[m[message.ID]] = message.Message(m)
		return sigs		
	
	def trust_signature(self, signature):
		db_sig = self.unverified_signature.find_one({message.ID:signature.id()})
		if not db_sig:
			log.error('signature %s not found in unverified signatures'%(signature.id()))
		self.unverified_signature.remove(db_sig)
		self.signature.insert(db_sig)
		
		msg = self.unverified_message.find_one({message.ID:signature.data[message.SIGNED_MESSAGE]})
		if not msg:
			log.error('message %s not found in unverified messages'%(signature.data[message.SIGNED_MESSAGE]))
			return False
		self.unverified_message.remove(msg)
		m = msg.copy()
		del m['_id']
		self.message.insert(msg)
		return message.Message(m)
	
	def add_signature_unussed(self, signature, msg_id):
		'add valid, verified signature to an existing message'
		if signature.data[message.SIGNED_MESSAGE] != msg_id:
			return False
			
		msg = self.message.find_one( {message.ID:msg_id} )
		if not msg:
			return None
		if not message.SIGNATURE_LIST in msg:
			msg[message.SIGNATURE_LIST] = {signature.id():signature.data}
		else:
			msg[message.SIGNATURE_LIST][signature.id()] = signature.data
		self.message.save(msg)

	def add_signature_unv(self, signature, msg_id):
		'add valid, verified signature to an existing message'
		return self.add_signature_to_table(msg_id, sigs_dict, self.unverified_message)
		
		msg = self.unverified_message.find_one( {message.ID:msg_id} )
		if not msg:
			return None
		if not message.SIGNATURE_LIST in msg:
			msg[message.SIGNATURE_LIST] = {signature.id():signature.data}
		else:
			msg[message.SIGNATURE_LIST][signature.id()] = signature.data
		self.unverified_message.save(msg)
		
	def add_message1(self, message, signatures):
		type = message['type']
		id = message['id']
		
		if type=='signature':
			msgid = message['message']
			msg = self.message.find_one({'id':msgid})
			if not msg:
				log.error('message %s for signature %s not found in local-db, drop signature'%(msgid, id))
				return False
			log.info('found message %s for signature %s'%(msgid, id))
			if not 'signature' in msg.keys():
				msg['signature'] = {id:message}
				self.message.save(msg)
				log.info('signature %s added to message %s in local-db'%(id, msgid))
				return True
			
			signs = msg['signature']
			for s in signs.keys():
				log.debug('signature %s'%(s,))
				
			if id in signs:
				log.info('signature %s already available'%(id,))
				return False
			signs[id] = message
			self.message.save(msg)
			log.info('signature %s added to message %s in local-db'%(id, msgid))
			return True
		
		msg = self.message.find_one({'id':id})
		if msg:
			log.info('message %s alraedy exists in local-db'%(msg,))
			return True
		
		#insert copy, so that original message is unmodified ( and lack _id key )
		self.message.insert(message.copy())
		log.info('message %s inserted to local-db'%(id,))
		return True
		
		existing_message = self.message.find_one({'id':message['id']})
		if existing_message:
			log.info('message %s already exist in the db, replacing with updated one'%(message['id'],))
			existing_message = message.copy()
			self.message.save(existing_message)
		else:
			self.message.insert(message.copy())
	
	def add_unverified_signature(self, signature):
		self.unverified_signature.insert(signature.copy())
		
if __name__ == '__main__':
	log = logging.getLogger('xmppdb')

	h = logging.StreamHandler()
	formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
	h.setFormatter(formatter)
	log.addHandler(h)
	log.setLevel(logging.DEBUG)

	db = Db()
	db.add_friend('testa')
	
