import client
import logging
import message

msg_list = []
objects = {}

log = logging.getLogger('xmppdb')

class Transport:
	def __init__(self, name, on_recv, on_status, on_user_command):
		self.name = name
		self.users = set()
		self.jid = name
		
		self.recv_cb = on_recv
		self.status_cb = on_status
		self.user_command_cb = on_user_command
		
		global objects
		objects[name] = self
	
	def connect(self, user):
		global objects
		if not user in objects:
			log.error('unknown user %s'%user)
			return
		if user in self.users:
			log.info('user %s already connected with %s'%(self.name, user))
			return
		
		log.info('user %s adds %s to list of friends'%(self.name, user))
		self.users.add(user)
		objects[user].connect(self.name)
	
	def send_all(self, msg):
		for user in self.users:
			self.send(user, msg)
	
	def send(self, to, msg):
		#log.info('%s -> %s [%s]'%self.name,to,msg)
		msg_list.append( (self.name, to, msg) )
	
	def add_user(self, jid):
		log.debug('request to add new jid %s'%(jid,))
		if not jid in self.users:
			log.info('user %s added new jid %s'%(self.name, jid))
			self.users.add(jid)
	
	def notify_owner(self, msg):
		'notify bot owner about new message he may be interested in'
		text = ''
		if message.PUBLIC_KEY in msg.data:
			text = 'public key'
		elif message.TEXT in msg.data:
			text = msg.data[message.TEXT]
		self.user_recv('message %s [%s]'%(msg.id(),text))
	
	def received(self, frm, msg):
		#log.info('%s <- %s [%s]'%self.name,frm,msg)
		self.recv_cb(frm, msg)
		
	def status(self, user, status):
		self.status_cb(user, status)
		
	def user_send(self, msg):
		'message send from bot owner'
		cmd, body = msg
		log.info('received from owner command %s, text %s'%(cmd,body))
		if cmd=='jid':
			log.info('request to add user %s'%body)
			self.connect(body)
		elif cmd=='y' or cmd=='Y':
			log.info('user accepted')
			self.user_command_cb('accept', body)
		elif cmd=='n':
			self.user_command_cb('reject', body)
		elif cmd=='accept':
			self.user_command_cb('accept', body)
		else:
			log.error('unknown command %s received'%cmd)
			self.user_command_cb()
	
	def user_recv(self, msg):
		'message bot send to user'
		log.info('sending message <%s> to user %s'%(msg,self.name))
		
#msg = (request, body)
#body = [msg]
#msg = (message, [signatures] )

{'id':0, 'public_key':1} # id
{'jid':0, 'owner':1} # jid
{'thread':[] }

def req_friend(msg):
	return ('friend', msg)

def req_put(msg):
	return ('put', msg)
	
class XmppDb:
	def __init__(self, name, auto_accept = False):
		self.name = name
		self.client = client.XmppClient(name, self.accept_selfsigned)
		self.transport = Transport(name, self.recv, self.status, self.user_command)
		self.users = set()
		self.auto_accept_selfsigned = auto_accept

		#self.fill_friends()
		
		# don't care who signed jid, it does not matter
		self.jid_msg = self.client.create_message({message.JID:self.transport.jid})
		
		self.pending_selfsigned = None
		
		self.db = self.client.db
	
	def accept_selfsigned(self, id):
		'invoked by client if the received id is selfsigned only, need to know'
		if self.auto_accept_selfsigned:
			return True
		self.pending_selfsigned = id
		self.transport.user_recv('user %s request your friendship. Accept? y/n'%(self.pending_selfsigned,))
		return False

	def recv(self, user, msg):
		request,body = msg
		if request == 'get':
			pass
		elif request == 'put':
			self.client.receive(body[0], body[1])
		elif request == 'friend':
			if user in self.users:
				log.info('friendship with %s established'%user)
				self.users.insert(user)
				self.fill_friends()
			#auto accept friends for now
			#self.client.receive(body[0], body[1])
			
		else:
			log.error('unknown request type %s'%(request,))
			return
		
		msgs = self.db.get_recent()
		for m in msgs:
			if message.JID in m.data:
				self.transport.add_user(m.data[message.JID])
			if m.data.has_key(message.TEXT) or m.data.has_key(message.PUBLIC_KEY):
				self.transport.notify_owner(m)
	
	def fill_friends(self):
		jids = self.client.get_friends()
		log.info('signed jids')
		for jid,_ in jids:
			log.info('jid %s'%jid)
	
	def send_jid_info(self, user):
		#prepare messag with user key
		m = (self.client.msg_public, {self.client.msg_public_selfsign.id():self.client.msg_public_selfsign})
		# ask to be freinds, and send our public key
		self.transport.send(user, req_put(m))
		# add our signed jid
		self.transport.send(user, req_put(self.jid_msg))
		
		#self.transport.send( user, req_friend(self.transport.jid) )
		
	def create(self, body):
		msg, sig = self.client.create_message(body)
		self.transport.send_all(req_put((msg,sig)))
	
	def status(self, user, status):
		pass
		
	def add_user(self, user):
		'command by external user'
		pass
	
	def user_command(self, cmd, body):
		'command received directly from the node user'
		if cmd=='accept':
			if body:
				log.info('owner request to accept user %s'%(body,))
				self.client.accept_messages_from(body)
			elif self.pending_selfsigned:				
				log.info('owner request to accept user %s'%(self.pending_selfsigned,))
				self.client.accept_messages_from(self.pending_selfsigned)
				self.pending_selfsigned = None
			else:
				log.error('nothing to accept')

def tick():
	'emulate real time ticks, and events happening ( message sedning/receving )'
	global msg_list
	global objects
	tmp = []
	tmp,msg_list = msg_list,tmp
	for frm,to,msg in tmp:
		objects[to].received(frm, msg)

print '\n\n\n'
jahera = XmppDb('jahera')
khalid = XmppDb('khalid', True)

khalid.send_jid_info('jahera')

tick()

jahera.transport.user_send( ('y',None) )
tick()

jahera.send_jid_info('khalid')
tick()

jahera.create({message.TEXT:'hey khalid, what\'s up'})
tick()
