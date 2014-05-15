import socket
import re
import Queue
import urllib2
import threading
import os
import logging
import config
import time
from BeautifulSoup import BeautifulSoup

class LinkBot:

	def __init__(self):
		self.server = config.server
		self.channels = config.channels
		self.nickname = config.nickname

		self.operational = True

		#self.q = Queue.Queue()

		self.urlReg = re.compile(r"(http://[^ ]+|https://[^ ]+)")
		self.channelReg = re.compile(r"(#[^ ]+)")

		self.operational = False

		logging.basicConfig(filename=config.logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)


	def run(self):
		self.connect()
		self.running = True

		while self.running:
			try:
				message = self.irc.recv(2040)
				message = message.strip('\n\r')
				logging.info("Recieved message: %s", message)
				if message != "":
					self.handleMessage(message)
			except socket.timeout:
				logging.warning("Connection lost, trying to reconnect")
				time.sleep(20)
				self.connect()

	def handleMessage(self, message):		
		#PingPong
		if message.find("PING") != -1:
			self.irc.send("PONG " + message.split()[1] + "\r\n")
			logging.debug("PONG")

		#Joining channels
		if message.find("End of /MOTD command.") != -1:
			for i in self.channels:
				self.irc.send("JOIN " + i + "\n")
				logging.info("Joined channel %s", i)
			self.operational = True

		#Ignoring private messages
		if len(message.split())>=3 and message.split()[2].find(self.nickname) != -1:
			logging.info("Message was private")
			private = True

		if self.operational:
			self.urlScan(message)


	def urlScan(self, message):
		private = False
		#Ignoring private messages
		if len(message.split())>=3 and message.split()[2].find(self.nickname) != -1:
			logging.info("Message was private")
			private = True

		if not private:
			url = self.urlReg.findall(message)
			#if url:
			for u in url:
				try:
					print "Found link " + u
					chanID = self.channels.index(self.channelReg.findall(message)[0])
					logging.info("Found link %s in %s", u, self.channels[chanID])
					t = threading.Thread(target=self.getTitle, args=(u.rstrip(), chanID))
					t.daemon = True
					t.start()
					#self.irc.send("PRIVMSG " + channel +" :"+ "Found url: " +u +"\n")
				
				except:
					logging.info("Couldn't parse message %s", message)


	def connect(self):
		try:
			self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.irc.settimeout(60*4)

			self.irc.connect((self.server, 6667))

			logging.info("Connected to server %s", self.server)


			self.irc.send("USER " + self.nickname + " " + self.nickname + " " + self.nickname + " :Linkbot\n")
			self.irc.send("NICK " + self.nickname + "\n")
			self.irc.send("PRIVMSG nickserv :NOOPE\r\n")

			logging.info("User and nicknames set")
		except socket.gaierror:
			logging.warning("Couldn't connect, trying again soon.")




	def getTitle(self, url, chanID):
		#Fetches title even when direct image link is posted
		imgurPicOnlyReg = re.compile(r"(http://|https://)i\.imgur\.com/[^ ]+(\.jpg|\.png|\.gif)")
		imgurPicOnly = imgurPicOnlyReg.findall(url)
		if imgurPicOnly:
			url=url[:-4]

		html = urllib2.urlopen(url).read()
		soup = BeautifulSoup(html)
		title = soup.title.string
		if isinstance(title, unicode):
			title = title.splitlines()
		else:
			title = title.rstrip(["\n","\r"])
		t = ""
		for i in title:
			t = t + i
		t = t.encode("utf-8").strip()
		print url + " " + str(t)
		message = url + " " + str(t)
		if (len(message) > 65):
			message = str(t)
		self.irc.send("PRIVMSG " + self.channels[chanID] + " : " + message +"\r\n")
		#self.q.put((message, chanID))


if __name__ == "__main__":
	bot = LinkBot()
	bot.run()