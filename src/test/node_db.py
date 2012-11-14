import sqlite3
import logging

log = logging.getLogger('infonet')

class Db:
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
		cur.execute("select count(*) from link where id_a=? and id_b=?", (id_a, id_b))
		r = cur.fetchone()
		return r and  r[0] > 0

	def set_linked(self, id_a, id_b):
		if self.is_linked(id_a, id_b):
			return
		self.conn.cursor().execute("insert into link (id_a, id_b) values (?, ?)", (id_a, id_b))

	def set_node_info(self, data):
		
		jid = data['jid']
		node_id = self.set_node(jid)
		
		#now add it's linked nodes
		for linked_node in data['link']:
			self.set_linked(node_id, self.set_node(linked_node))
		
	def remove_links(self, jid):
		node_id = self.get_node_id(jid)
		if not node_id:
			return False
		self.cur.execute('delete from link where id_a=?', (node_id,))
		return True
		
	def get_linked_nodes(self, jid):
		
		node_id = self.get_node_id(jid)
		if not node_id:
			return None
		
		cur = self.conn.cursor()
		cur.execute("select node.jid from node join link on node.id = link.id_b where link.id_a = ?", (node_id,))
		return [r[0] for r in cur.fetchall()]
		

x = Db()
if x.set_node('test'):
	print 'ok'
if x.set_node('test'):
	print 'ok'
