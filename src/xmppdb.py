import client
import logging

msg_list = []
objects = {}


log = logging.getLogger('xmppdb')

class Transport:
	def __init__(self, name, on_recv, on_status):
		self.name = name
		self.users = {}
		
		self.recv_cb = on_recv
		self.status_cb = on_status
		
		global objects
		objects[name] = self
	
	def send(self, to, msg):
		#log.info('%s -> %s [%s]'%self.name,to,msg)
		msg_list.append( (self.name, to, msg) )
		
	def received(self, frm, msg):
		#log.info('%s <- %s [%s]'%self.name,frm,msg)
		self.recv_cb(frm, msg)
		
	def status(self, user, status):
		self.status_cb(user, status)
		
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
		self.transport = Transport(name, self.recv, self.status)
		self.users={}
	
	def recv(self, user, msg):
		request,body = msg
		if request == 'get':
			pass
		elif request == 'put':
			self.client.receive(body[0], body[1])
		else:
			log.error('unknown request type %s'%(request,))
	
	def friend(self, user):
		#prepare messag with user key
		m = (self.client.msg_public, [self.client.msg_public_selfsign])
		self.transport.send(user, req_friend(m))
		
	def create(self, body):
		msg, sig = self.client.create_message(body)
		self.transport.send(user, req_put(m))
	
	def status(self, user, status):
		pass
		
	def add_user(self, user):
		'command by external user'
		pass

def tick():
	'emulate real time ticks, and events happening ( message sedning/receving )'
	global msg_listc
	global objects
	tmp = []
	tmp,msg_list = msg_list,tmp
	for frm,to,msg in tmp:
		objects[to].received(frm, msg)

jahera = XmppDb('jahera')
khalid = XmppDb('khalid')

jahera.friend('khalid')
khalid.friend('jahera')