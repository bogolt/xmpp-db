import json
import logging

log = logging.getLogger('infonet')

h = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
h.setFormatter(formatter)
log.addHandler(h)
log.setLevel(logging.DEBUG)

class Transport:
	def __init__(self, owner):
		self.owner = owner
	
	def send(self, jid, data):
		pass
		
	def received(self, jid, data):
		pass
		
	def link(self, jid):
		pass

	def unlink(self, jid):
		pass
		


class LocalTransport(Transport):
	
	pipe = []
	nodes = {}
	
	def __init__(self, owner):
		Transport.__init__(self, owner)
		LocalTransport.nodes[owner.jid] = self
		log.info('register node %s'%(owner.jid,))
		
	def __del__(self):
		log.info('unregister node %s'%(owner.jid,))
		del LocalTransport.nodes[owner.jid]
		
	def send(self, jid, data):
		LocalTransport.pipe.append( (jid, self.owner.jid, data) )
		
	def received(self, jid, data):
		self.owner.received(jid, data)
		
	def status_changed(self, jid, online):
		self.owner.status_changed(jid, online)
		
	def link(self, jid):
		LocalTransport.nodes[jid].status_changed(self.owner.jid, True)
		return True

	def unlink(self, jid):
		LocalTransport.nodes[jid].status_changed(self.owner.jid, False)
		return True
		
def tick():
	pp, LocalTransport.pipe = LocalTransport.pipe, []
	for transf in pp:
		LocalTransport.nodes[transf[0]].received( transf[1], transf[2] )

def make_request_linked_nodes(jid):
	return {'request':{'type':'linked-nodes', 'jid':jid}}

def make_linked_node(jid):
	return {'linked-node':jid}

class Node:
	def __init__(self, jid, transportType):
		self.jid = jid
		self.linked = set()
		
		self.block_list = set()
		
		self.transport = transportType(self)
	
	def link(self, jid):
		if jid in self.linked:
			log.error('jid %s already linked to %s'%(jid, self.jid))
			return False
		self.transport.link(jid)
		self.linked.add(jid)
		log.info('jid %s is now linked with %s'%(jid, self.jid))
		return True
		
	def unlink(self, jid):
		if jid in self.linked:
			self.transport.unlink(jid)
			self.linked.remove(jid)
			log.info('removing jid %s from %s linked list'%(jid, self.jid))
			return True
		log.error('jid %s not found in %s linked list - unable to remove'%(jid, self.jid))
		return False
		
	def send(self, to_node, msg):
		self.transport.send(to_node, json.dumps(msg))
		
	def status_changed(self, jid, online):
		log.info('node %s see %s as %s'%(self.jid, jid, 'online' if online else 'offline'))
		
		if online:
			self.requestLinkedNodes(jid)
			self.updateLinkedNodes(jid)
			
	def requestLinkedNodes(self, jid):
		self.send(jid, make_request_linked_nodes(jid))
		
	def updateLinkedNodes(self, jid):
		for node in self.linked:
			if node != jid:
				self.send( node, make_linked_node(jid) )
		
	def received(self, from_node, msg):
		log.info("node %s received message from %s: %s"%(self.jid, from_node, msg))
		try:
			message = json.loads(msg)
			self.process_message(from_node, message)
		except TypeError as e:
			log.error("json parse error: %s"%(e,))
			self.block_list.add(from_node)
			self.unlink(from_node)
	
	def make_node_info(self):
		return {'node':{'jid':self.jid, 'link':[node for node in self.linked]}}
		
	
	def process_message(self, jid, msg):
		for key, data in msg.items():
			if key == 'node':
				self.processNodeInfo(jid, data)
			elif key == 'request':
				if data['type'] == 'linked-nodes':
					self.processLinkedNodesRequest(jid, data)
			elif key == 'linked-node':
				self.processLinkedNodeInfo(jid, data)
	
	def processNodeInfo(self, jid, node):
		pass
	
	def processLinkedNodesRequest(self, jid, data):
		pass
		
	def processLinkedNodeInfo(self, jid, node):
		pass
	
	

def makeLinkedNodes(keys, transport):
	prev = None
	prevKey = None
	nodes = []
	for key in keys:
		node = Node(key, transport)
		nodes.append(node)
		if prev:
			prev.link(key)
			node.link(prevKey)
		prevKey = key
		prev = node
	return nodes

alpha = makeLinkedNodes([chr(x) for x in range(ord('a'), ord('z')+1)], LocalTransport)
tick()

#log.info(':: %s'%(a.make_node_info()))
