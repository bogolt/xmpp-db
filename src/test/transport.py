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
	
	def send(self, to, msg):
		log.info('%s->%s, msg: %s'%(self.name, to, msg))
		async_send(self.name, to, msg)
	
	def receive(self, fr, msg):
		log.info('%s<-%s, msg: %s'%(self.name, fr, msg))
	

def test_msgs():
	x = Node('x')
	y = Node('y')
	x.send(y.name, 'hey')
	x.send(y.name, 'heyyou')
	step()
	
test_msgs()
