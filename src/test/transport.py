import logging

log = logging.getLogger('xmppdb')

h = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
h.setFormatter(formatter)
log.addHandler(h)
log.setLevel(logging.DEBUG)

node_dict = {}
pending_msg_list = []

def async_send(sender, receiver, msg):
	global pending_msg_list
	pending_msg_list.append( (sender, receiver, msg) )
	
def register_node(node):
	global node_dict
	if not node.name in node_dict:
		log.info('node %s registered'%(node.name,))
		node_dict[node.name] = node

def step():
	global node_dict
	global pending_msg_list
	
	tmp = []
	tmp,pending_msg_list = pending_msg_list,tmp
	
	log.info('-'*30)
	
	for sender,receiver,msg in tmp:
		node_dict[receiver].receive(sender, msg)

class Node:
	def __init__(self, name):
		self.name = name
		register_node(self)
		self.connected = set()
		
	def add_node_manually(self, node):
		log.info('adding node %s'%(node,))
		self.register_node(node)
		
	def register_node(self, node):
		log.info('registering node %s'%(node,))
		self.connected.add(node)
		self.send(node, 'register')
	
	def send(self, to, msg):
		if not to in self.connected:
			log.error('node %s unable to send message to %s - not connected'%(self.name, to))
			return False
		log.info('%s->%s, msg: %s'%(self.name, to, msg))
		async_send(self.name, to, msg)
	
	def receive(self, fr, msg):
		log.info('%s<-%s, msg: %s'%(self.name, fr, msg))
		if msg.startswith('ask_nodes'):
			log.info('node %s asks for nodes'%(fr,))
			self.send_nodes(fr)
		elif msg.startswith('register'):
			log.info('node %s ask to register with it'%(fr,))
			self.connected.add(fr)
			#self.update_known_nodes()
		elif msg.startswith('node_info '):
			log.info('%s got node info %s'%(self.name, msg[len('node_info '):]))
	
	def ask_nodes(self, to):
		'ask dest node for more nodes from it'
		log.info('%s->%s, ask nodes'%(self.name, to))
		self.send(to, 'ask_nodes')
		
	def send_nodes(self, to):
		'send dest node available nodes'
		log.info('sending nodes to %s'%(to,))
		for node in self.connected:
			self.send(to, 'node_info %s'%(node,))

def test_msgs():
	x = Node('x')
	y = Node('y')
	x.add_node_manually('y')
	x.send(y.name, 'hey')
	x.send(y.name, 'heyyou')
	step()
	
def test_connet():
	x = Node('a')
	y = Node('b')
	z = Node('c')
	
	x.add_node_manually('b')
	y.add_node_manually('c')
	
	x.ask_nodes('b')
	step()
	step()
	
#test_msgs()
test_connet()
