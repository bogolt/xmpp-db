import crypto
import logging
import base64

log = logging.getLogger('xmppdb')

ID = 'id'
HASH_TYPE='hash_type'
SIGNATURE_LIST='signatures'
PUBLIC_KEY='public_key'
SIGNATURE='signature'
USER='user'
SIGNED_MESSAGE='signed_message'
JID='jid'
TYPE='type'
TEXT='text'

def exteract_value(message, name):
	value = message[name]
	if not value:
		log.error('message does not contain %s as expected'%(name,))
		return None
	return value

def plain(message):
	keys = message.keys()
	keys.sort()
	s = ''
	for key in keys:
		s+='%s%s'%(key, message[key])
	return s

def calculate_hash(message):
	hash_type = None
	if HASH_TYPE in message:
		hash_type = message[HASH_TYPE]
	m = plain(message)
	h = crypto.hash(m, hash_type)
	return h
	
def hash_message(message):
	msg = message
	id = calculate_hash(msg)
	msg[ID] = id
	return msg

def verify_hash(message):
	id = message[ID]
	if not id:
		log.error('no id defined for message %s'%(message,))
		return False
	msg = message.copy()
	del msg[ID]
#	if SIGNATURE_LIST in msg:
#		del msg[SIGNATURE_LIST]

	hash = calculate_hash(msg)
	return hash == id
	
class Message:
	def __init__(self, keys_values):
		self.data = keys_values.copy()
		if '_id' in self.data:
			del self.data['_id']
	
	def __str__(self):
		#s = []
		#for k,v in self.data.items():
		#	s.append('%s=%s'%(k,v))
		#return ';'.join(s)
		return ' '.join(['%s=%s'%(k,v) for k,v in self.data.items()])
	
	def is_valid(self):
		if not ID in self.data:
			return False
		return verify_hash(self.data)
	
	def id(self):
		if not ID in self.data:
			return self.hash()
		return self.data[ID]
	
	def hash(self):
		if ID in self.data:
			log.error('message already contains id')
			return False
		self.data = hash_message(self.data)		
		return self.id()
	
	def sign(self, key, user):
		id = self.id()
		if not id:
			return None
		signature_value = key.sign(id)
		if not signature_value:
			return None
			
		signature = Message({SIGNATURE:base64.b64encode(signature_value), USER:user.id(), SIGNED_MESSAGE:id})
		signature.hash()
		return signature

def sign_message(message_id, private_key, user):
	signature_value = private_key.sign(message_id)
	msg = Message({SIGNATURE:base64.b64encode(signature_value), USER:user.id(), SIGNED_MESSAGE:message_id})
	msg.hash()
	return msg
	
def generate_public_key_message(key):
		pub_key_data = ''
		if isinstance(key, crypto.PrivateKey):
			pub_key_data = base64.b64encode( key.public_key.serialize() )
		else:
			return None
		msg = Message({PUBLIC_KEY:pub_key_data})
		msg.hash()
		return msg

#def get_signature(signatures, user_id):
#	if not user_id in signatures:
#		return None
#	return signatures[user_id]

def is_signature_message_valid(signature, msg_id):
	s = signature.data
	#log.debug('verifying signature %s for message %s'%(s, msg_id))
	if not ID in s:
		return False
	if not SIGNED_MESSAGE in s:
		return False
	if s[SIGNED_MESSAGE] != msg_id:
		return False
	if not USER in s:
		return False
	return True


def message_to_dict(msg):
	if not msg:
		return None
	return {msg.id():msg.data.copy()}

def message_dict_to_plain(msg):
	m_dict = []
	for m in msg.values():
		if isinstance(m, Message):
			m_dict.append(m.data.copy())
		else:
			m_dict.append(m)
	
	return m_dict
		

def to_message_dict(messages):	
	msg_dict = {}
	if not messages:
		return msg_dict
	for msg in messages:
		msg_dict[msg[ID]] = Message(msg)
	return msg_dict
