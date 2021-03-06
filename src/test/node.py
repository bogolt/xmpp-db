import json
import logging
import node_db

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
	
def make_request(req, jid):
	return {'request' : { 'jid':jid, 'type':req} }

class Node:
	#number of user circles stored in node memory
	N = 3
	
	Neighbors = 0
	MaxDistance = 3
	
	def __init__(self, jid, transportType):
		self.jid = jid
		self.db = node_db.Db()
		self.db.set_self(self.jid)
		
		self.transport = transportType(self)
	
	def link(self, jid):
		if self.transport.link(jid):
			#self.db.add_node(jid, True)
			#self.linked_nodes[Node.NodeNeighbors].add(jid)
			log.info('[%s] connected with %s'%(self.jid, jid))
			return True
		
		log.error('[%s] can not connect with %s'%(self.jid, jid))
		return False
		
	def unlink(self, jid):
		
		if self.transport.unlink(jid):
			#self.linked_nodes[Node.NodeNeighbors].remove(jid)
			log.info('[%s] disconnected from %s'%(self.jid, jid))
			return True
			
		log.error('[%s] can not disconnect from %s'%(self.jid, jid))
		return False
		
	def send(self, to_node, msg):
		self.transport.send(to_node, json.dumps(msg))
		
	def status_changed(self, jid, online):
		log.info('[%s] %s %s'%(self.jid, jid, 'available' if online else 'unavailable'))
		is_new_node = self.db.set_node_status(jid, online, is_linked = True)
		
		if online:
			self.requestNodeInfo(jid)
		# reconnect with it's friends		
			
	def requestLinkedNodes(self, jid):
		self.send(jid, make_request_linked_nodes(jid))
	
	def requestNodeInfo(self, jid, other_jid = None):
		self.send(jid, make_request('node-info', other_jid if other_jid else jid))
		
	#def updateLinkedNodes(self, jid):
	#	for node in self.linked_nodes[Node.NodeNeighbors]:
	#		if node != jid:
	#			self.send( node, make_linked_node(jid) )
	#			self.send( node, make_linked_node(jid) )
		
	def received(self, from_node, msg):
		#log.info("[%s] got msg received message from %s: %s"%(self.jid, from_node, msg))
		message = None
		try:
			message = json.loads(msg)
		except TypeError as e:
			log.error("json parse error: %s"%(e,))
			self.block_list.add(from_node)
			self.unlink(from_node)
		if message:
			self.process_message(from_node, message)
	
	def make_node_info(self, jid):
		#log.info('%s requested nodes of %s'%(self.jid, jid))
		linked = self.db.get_linked_nodes(jid)
		#log.info('%s got linked nodes for %s %s'%(self.jid, jid, linked))
		if not linked:
			return {'node':{'jid':jid, 'error':'unknown'}}
		return {'node':{'jid':jid, 'link': linked } }
	
	def process_message(self, jid, msg):
		for key, data in msg.items():
			if key == 'node':
				self.processNodeInfo(jid, data)
			elif key == 'request':
				if data['type'] == 'linked-nodes':
					self.processLinkedNodesRequest(jid, data)
				elif data['type'] == 'node-info':
					self.processNodeInfoRequest(jid, data)
			elif key == 'linked-node':
				self.processLinkedNodeInfo(jid, data)

	def processNodeInfoRequest(self, jid, node):
		log.info('[%s] request from %s to get node info of %s'%(self.jid, jid, node['jid'],))
		self.send(jid, self.make_node_info(node['jid']))
	
	def processNodeInfo(self, jid, data):
		if 'error' in data:
			log.error('[%s] request from %s failed to get node %s info'%(self.jid, jid, data['jid']))
			return
		log.info('[%s] from %s node info: %s'%(self.jid, jid, data))
		newly_linked = self.db.set_node_info(data)
		for node in newly_linked:
			if node == jid or node == self.jid:
				continue
			dist = self.db.get_distance(self.jid, node)
			if dist:
				if dist < Node.MaxDistance:
					log.info('[%s] request %s newly linked node %s'%(self.jid, jid, node))
					self.requestNodeInfo(jid, node)
				#else:
				#	log.info('[%s] connecting to node %s / distance %s'%(self.jid, node, dist))
				#	self.link(node)
	
	def processLinkedNodesRequest(self, jid, data):
		log.info('[%s] request from %s to get linked node info of %s'%(self.jid, jid, node['jid'],))
		self.send(jid, self.make_node_info(self.jid))
		
	def processLinkedNodeInfo(self, jid, node):
		pass
		
	def show_linked(self):
		known = self.db.get_nodes()
		print '[%s] %s'%(self.jid, known)
		for node in known:
			linked = self.db.get_linked_nodes(node)
			print '-- %s %s'%(node, linked)
			for ln in linked:
				print '--- [%s, %s] = %s'%(self.jid, ln, self.db.get_distance(self.jid, ln))
				
	def connect_distant(self):
		

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

alpha = makeLinkedNodes([chr(x) for x in range(ord('a'), ord('k')+1)], LocalTransport)
tick()
tick()
tick()
tick()
tick()
tick()
tick()
#for node in alpha:
#	node.requestNodes(1)

#alpha[1].requestNodeInfo('c', 'd')

for a in alpha:
	a.show_linked()

#log.info(':: %s'%(a.make_node_info()))
