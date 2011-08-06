#!/usr/bin/python

import random
import string

import xmpp
import xmpp.features

import sys, traceback
import logging
import ConfigParser

import db

from jabberbot import JabberBot, botcmd

log = logging.getLogger('xmppdb')

h = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
h.setFormatter(formatter)
log.addHandler(h)
log.setLevel(logging.DEBUG)


bot_password_length = 16
config_file = 'xmpp_db.cfg'

def register_user(id, password):
	'register new user on jabber server'
	jid = xmpp.JID(id)
	c = xmpp.Client(jid.getDomain())
	
	#client must be connected, in order for dispatcher object to exist
	c.connect()
	return xmpp.features.register(c.Dispatcher, jid.getDomain(), {'username':jid.getNode(), 'password':password})

def gen_password(length=8, chars=string.letters + string.digits+'_:,"\'@!#$%^&*()-=+[]{}/\\'):
    return ''.join([random.choice(chars) for i in range(length)])


class XmppTransport(JabberBot):
	def __init__(self, bot_owner, username, password):
		JabberBot.__init__(self, username, password, True)
		self.owner = bot_owner

		# create console handler
		chandler = logging.StreamHandler()
		# create formatter
		formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
		# add formatter to handler
		chandler.setFormatter(formatter)
		# add handler to logger
		self.log.addHandler(chandler)

		self.log.setLevel(logging.INFO)
		#self.log.info( 'xmpp-db-bot %s starting, owner jids: %s' % (username, bot_owner))

	def connected(self):
		'called from outside the class to notify of connected status'
		log.info('connected to server')

		for jid in self.roster.getItems():
			log.info('user %s is %s, subscr %s'%(jid, self.roster.getStatus(jid), self.roster.getSubscription(jid)))

		self.add_owner()
	
	def add_owner(self):
		for jid in self.owner:
			if jid in self.roster.getItems():
				continue
		log.info('adding owner jid %s to roster'%(jid,))
		self.roster.Subscribe(jid)
	
	def is_jid_owner(self, jid):
		for j in self.owner:
			if jid.bareMatch(j):
				return True
		return False
	
	def status_type_changed(self, jid_obj, new_status_type):
		'someone changed his status'
		
		JabberBot.status_type_changed(self, jid_obj, new_status_type)
		
		#don't care about owner status change
		if self.is_jid_owner(jid_obj):
			return
		
		jid = jid_obj.getStripped()
		log.info('user %s %s %s'%(jid,self.roster.getStatus(jid), self.roster.getShow(jid)))
		
		self.send_owner('user %s is connected'%(jid_obj,))
			
	def send_owner(self, msg):
		for jid in self.owner:
			log.info('owner jid %s is %s'%(jid, self.roster.getStatus(jid)))
			#TODO: send here

	def prepare_message(self, msg, prefix, is_owner):
		sender = msg.getFrom()
		if is_owner != self.is_jid_owner(sender):
			return False, False
		words = msg.getBody().split()
		body = ''
		if len(words) > 1:
			body = msg.getBody()[len(prefix)+1:]
		return (sender, body)

	@botcmd
	def status(self, message, args):
		'get the current status'
		sender,body = self.prepare_message(message, 'status', True)
		if not sender:
			return 'unauthorized user jid %s'%(message.getFrom(),)

		log.debug('status request received from owner jid %s'%(sender,))
		return 'roster: %s'%(self.roster.getItems(),)

	@botcmd
	def add(self, message, args):
		'add new friend'
		sender,jid = self.prepare_message(message, 'add', True)
		if not sender:
			return 'unauthorized user jid %s'%(message.getFrom(),)
		
		log.info('adding jid %s', jid)
		self.roster.Subscribe(jid)
		return 'adding jid %s to list of known users'%(jid,)
	
	@botcmd
	def remove(self, message, args):
		'remove friend'
		sender,jid = self.prepare_message(message, 'remove', True)
		if not sender:
			return 'unauthorized user jid %s'%(message.getFrom(),)
		
		log.info('removing jid %s', jid)
		self.roster.Subscribe(jid)
		return 'removing jid %s from list of known users'%(jid,)

def write_config(conf):
	with open(config_file, 'wb') as configfile:
		config.write(configfile)

if __name__ == '__main__':
	log.info('xmpp-db started')

	config = ConfigParser.SafeConfigParser()
	config.read(config_file)

	bot_username = config.get('bot', 'user')
	bot_password = config.get('bot', 'password')
	bot_owner = config.get('bot', 'owner')
	
	if not bot_username:
		log.error('bot username is not specified')
		exit()
		
	if not bot_owner:
		log.error('bot owner is not specified')
		exit()
	
	if not bot_password:
		log.info('registering JID %s'%(bot_username,))
		bot_password = gen_password(bot_password_length)
		if not register_user(bot_username, bot_password):
			log.error('registration of %s failed, try another username and/or server'%(bot_username,))
			exit()
		log.info('bot %s registered, saving password'%(bot_username))
		config.set('bot', 'password', bot_password)
		write_config(config)

	owner = config.get('bot', 'owner')

	try:
		own = owner.split(',; ')
		log.info('owner is %s'%(own,))
		bot = XmppTransport(own, bot_username, bot_password)
		bot.serve_forever(bot.connected)
	except:
		traceback.print_exc(file=sys.stdout)
	
	log.info('xmpp-db stopped')
