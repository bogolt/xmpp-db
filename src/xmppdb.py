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
		self.jid = '%s@test.org'%name
		
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
	
	def send(self, to, msg):
		#log.info('%s -> %s [%s]'%self.name,to,msg)
		msg_list.append( (self.name, to, msg) )
		
	def received(self, frm, msg):
		#log.info('%s <- %s [%s]'%self.name,frm,msg)
		self.recv_cb(frm, msg)
		
	def status(self, user, status):
		self.status_cb(user, status)
		
	def user_send(self, msg):
		'message send from bot owner'
		cmd, body = msg
		if cmd=='jid':
			log.info('request to add user %s'%body)
			self.connect(body)
		else:
			log.error('unknown command %s received'%cmd)
		
		
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
	def __init__(self, name):
		self.name = name
		self.client = client.XmppClient(name)
		self.transport = Transport(name, self.recv, self.status, self.user_command)
		self.users = set()
		#self.fill_friends()
		
		# don't care who signed jid, it does not matter
		self.jid_msg = self.client.create_message({message.JID:self.transport.jid})
	
	
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
		self.transport.send(user, req_put(m))
	
	def status(self, user, status):
		pass
		
	def add_user(self, user):
		'command by external user'
		pass
	
	def user_command(self, cmd, body):
		'command received directly from the node user'
#		if cmd=='jid':
#			self.transport.

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
khalid = XmppDb('khalid')

khalid.transport.user_send( ('jid', 'jahera') )

#jahera.send_jid_info('khalid')
#khalid.friend('jahera')
tick()
tick()
tick()
