import sqlite3
import logging

log = logging.getLogger('infonet')

class Db:
	
	MaxDepth = 3
	
	def __init__(self, dbpath=":memory:"):
		self.conn = sqlite3.connect(dbpath)				
		self.node_id = None
		self.jid = None
		
		self.prepare()

	def set_self(self, jid):
		self.node_id = self.set_node(jid)
		self.jid = jid
		self.set_node_status(jid, True)

	def prepare(self):
		cur = self.conn.cursor()
		cur.execute("""create table if not exists node(
					id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
					jid text,
					is_online integer(1)
					)""")
					
		cur.execute("""create table if not exists link(
					id_a INTEGER NOT NULL,
					id_b INTEGER NOT NULL
					)""")
					
	
	def get_node_id(self, jid):
		cur = self.conn.cursor()
		
		cur.execute("select id from node where jid=?", (jid,))
		r = cur.fetchone()
		if r:
			return int(r[0])
		return None		
	
	def add_node(self, jid):
		self.conn.cursor().execute("insert into node(jid) values (?)", (jid,))
		return self.get_node_id(jid)
	
	def set_node(self, jid):
		node_id = self.get_node_id(jid)
		if node_id:
			return node_id
		return self.add_node(jid)
	
	def set_node_status(self, jid, online_status = True, is_linked = False):
		
		node_id = self.set_node(jid)
		
		cur = self.conn.cursor()
		cur.execute("select is_online from node where id=?", (node_id,))
		for is_online in cur.fetchall():
			if is_online == online_status:
				return False
			cur.execute("update node set is_online=? where id=?", (online_status, node_id))
		
		if not online_status:
			self.remove_links(jid)
		elif is_linked:
			self.set_linked(self.node_id, node_id)
		
		return True

	def is_linked(self, id_a, id_b):
		cur = self.conn.cursor()
		cur.execute("select count(*) from link where (id_a=? and id_b=?) or (id_a=? and id_b=?)", (id_a, id_b, id_b, id_a))
		r = cur.fetchone()
		return r and  r[0] > 0

	def set_linked(self, id_a, id_b):
		if self.is_linked(id_a, id_b):
			return False
		self.conn.cursor().execute("insert into link (id_a, id_b) values (?, ?)", (id_a, id_b))
		self.conn.cursor().execute("insert into link (id_a, id_b) values (?, ?)", (id_b, id_a))
		return True
		
	def set_node_info(self, data):
		
		jid = data['jid']
		node_id = self.set_node(jid)
		
		#now add it's linked nodes
		newly_linked = set()
		for linked_node in data['link']:
			if self.set_linked(node_id, self.set_node(linked_node)):
				if self.jid != linked_node:
					newly_linked.add( linked_node )
		return newly_linked
		
	def remove_links(self, jid):
		node_id = self.get_node_id(jid)
		if not node_id:
			return False
		self.cur.execute('delete from link where id_a=?', (node_id,))
		return True
		
	def get_linked_layer_nodes(self, jid, layer = 1):
		node_id = self.get_node_id(jid)
		#if not node_id:
		#	return None
			
		#for l in range(0, layer):
		#	layers = self.get_linked_ids(node_id)
		#	for j in layers:
		#		nid = self.get_node_id(j)
		#		self.get_linked_nodes(nid)
	
	def get_linked_ids(self, node_id):
		cur = self.conn.cursor()
		cur.execute("select id_b from link where id_a = ?", (node_id,))
		layer = set()
		for r in cur.fetchall():
			layer.add(int(r[0]))
		return layer
		
	def get_distance(self, jid_a, jid_b):
		if jid_a == jid_b:
			return 0
			
		id_a = self.get_node_id(jid_a)
		if not id_a:
			log.error('jid %s not found in db'%(jid_a))
			return None
		
		id_b = self.get_node_id(jid_b)
		if not id_b:
			log.error('jid %s not found in db'%(jid_b))
			return None
		
		return self.get_id_distance(id_a, id_b, 0)
		
	
	def get_id_distance(self, a, b, depth):
		if depth > Db.MaxDepth:
			return None
			
		if self.is_linked(a, b):
			return 1
		ids_a = self.get_linked_ids(a)
		
		dist = None
		for id_a in ids_a:
			d = self.get_id_distance(id_a, b, depth + 1)
			if d and (not dist or d < dist):
				dist = d
		if not dist:
			return None
		return dist + 1
		
		
	def get_linked_nodes(self, jid):
		
		node_id = self.get_node_id(jid)
		if not node_id:
			return None
		
		cur = self.conn.cursor()
		cur.execute("select node.jid from node join link on node.id = link.id_b where link.id_a = ?", (node_id,))
		return [r[0] for r in cur.fetchall()]
		
	def get_nodes(self):
		cur = self.conn.cursor()
		cur.execute("select node.jid from node")
		return [r[0] for r in cur.fetchall()]
		

x = Db()
if x.set_node('test'):
	print 'ok'
if x.set_node('test'):
	print 'ok'
