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
		
class NodeDb:
	def __init__(self, name):
		self.name = name
		
	
	#def setNodeInfo(self, node):
		

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
		self.nodes = {}
		
		self.block_list = set()
		
		self.transport = transportType(self)
	
	def link(self, jid):
		if self.transport.link(jid):
			self.linked.add(jid)
			log.info('%s--%s linked OK'%(self.jid, jid))
			return True
		
		log.error('%s-|-%s'%(self.jid, jid))
		return False
		
	def unlink(self, jid):
		
		if self.transport.unlink(jid):
			self.linked.remove(jid)
			log.info('%s||%s unlinked OK'%(self.jid, jid))
			return True
			
		log.error('%s-||-%s'%(self.jid, jid))
		return False
		
	def send(self, to_node, msg):
		self.transport.send(to_node, json.dumps(msg))
		
	def status_changed(self, jid, online):
		log.info('node %s see %s as %s'%(self.jid, jid, 'online' if online else 'offline'))
		
		if online:
			self.linked.add(jid)
			if not jid in self.nodes:
				self.nodes[jid] = {}
			
			self.requestLinkedNodes(jid)
			self.updateLinkedNodes(jid)
			
		else:
			self.linked.remove(jid)
			
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
	
	def make_node_info(self, jid):
		if jid == self.jid:
			return {'node':{'jid':self.jid, 'link':[node for node in self.linked]}}
		if not jid in self.nodes:
			return {'node':{'jid':self.jid, 'error':'unknown'}}
		
		return {'node':{'jid':self.jid, 'link':[{'jid':node,'link':len(links)} for node,links in self.nodes[jid].items()]}}
	
	
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
		friends = {}
		for n in node['link']:
			friends[n] = (0,0)
		self.nodes[node['jid']] = friends
		
		#analyse distance
		#nodes = self.getDistantNode()
		#for node in nodes:
		n = self.getDistantNode()
		if n:
			self.link(n)
			
	def getDistantNode(self):
		for prime in self.linked:
			if not prime in self.nodes:
				continue
			
			for node in self.nodes[prime]:
				if node in self.linked:
					continue
					
			
	
	def processLinkedNodesRequest(self, jid, data):
		self.send(jid, self.make_node_info(self.jid))
		
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

alpha = makeLinkedNodes([chr(x) for x in range(ord('a'), ord('c')+1)], LocalTransport)
tick()
tick()
tick()

#log.info(':: %s'%(a.make_node_info()))
