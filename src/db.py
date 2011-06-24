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
		
		# signatures which does not have public key ( yet )
		self.unverified_signature = self.db.unverified_signature
		
		# message without verified signatures
		self.unverified_message = self.db.unverified_message
		
		#log.info('Debug - remove all entries before use')
		self.message.remove()
		
		self.unverified_signature.remove()
		self.unverified_message.remove()
		
		self.show()
		
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
		
	def get_message_from_table(self, id, table):
		'get message from given table'
		msg = table.find_one({'id':id})
		if not msg:
			return None, None
		log.debug('db message found %s'%(msg,))
		m = msg.copy()
		del m['_id']
		signatures = None
		if message.SIGNATURE_LIST in m:
			signatures = m[message.SIGNATURE_LIST].copy()
			del m[message.SIGNATURE_LIST]
		return message.Message(m),message.to_message_dict(signatures)
		
	def add_message_to_table(self, msg, sigs, table):
		'add message to table, consider there is no such message yet'
		#there is no point in adding existing message, so no verification is done
		#to add signatures to an existing message, use add_signatures
		
		m = msg.data.copy()
		if sigs:
			si = {}
			if isinstance(sigs, message.Message):
				si[sigs.id()] = sigs.data.copy()
			else:
				for s in sigs.values():
					si[s.id()] = s.data
				
			m[message.SIGNATURE_LIST] = {}
			m[message.SIGNATURE_LIST].update(si)
			
		table.insert(m)
	
	def add_signature_to_table(self, msg, signatures, table):
		'add more signatures to an existing message'
		msg_id = None
		if isinstance(msg, message.Message):
			msg_id = msg.id()
		else:
			msg_id = msg
		m = table.find_one({message.ID:msg_id})
		if not m:
			log.error('message %s not found in db'%(msg.id()))
			return None
		if not message.SIGNATURE_LIST in m:
			m[message.SIGNATURE_LIST] = {}
		old_signatures_count = len(m[message.SIGNATURE_LIST])
		m[message.SIGNATURE_LIST].update(message.message_dict_to_plain(signatures))
		new_signatures_count = len(m[message.SIGNATURE_LIST])
		if old_signatures_count == new_signatures_count:
			log.info('no new signatures added, to message %s'%(msg_id))
			return None
		log.info('adding %s new signatures to message %s'%((new_signatures_count - old_signatures_count), msg_id))
		table.save(m)
		
	def get_message(self, id):
		'get verified and signed message with its signature if available'
		return self.get_message_from_table(id, self.message)
		
		
		msg = self.message.find_one({'id':id})
		if not msg:
			return None, None
		log.debug('db message found %s'%(msg,))
		m = msg.copy()
		del m['_id']
		signatures = None
		if message.SIGNATURE_LIST in m:
			signatures = m[message.SIGNATURE_LIST].copy()
			del m[message.SIGNATURE_LIST]
		return message.Message(m),message.to_message_dict(signatures)
	
	def add_message(self, msg, signature = None):
		'no verification requied, considered message is yet unknown'
		return self.add_message_to_table(msg, signature, self.message)

	def add_message_unv(self, msg, signature = None):
		'no verification requied, considered message is yet unknown'
		return self.add_message_to_table(msg, signature, self.unverified_message)
	
	def add_signatures(self, sigs_dict, msg_id):
		'add dict of signatures for one single message'
		return self.add_signature_to_table(msg_id, sigs_dict, self.message)
		
		
		for signature in sigs_dict.values():
			self.add_signature(signature, msg_id)
	
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
	
