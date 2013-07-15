import socket
import re
import Queue
import urllib2
import threading
import os
import logging
import config
from BeautifulSoup import BeautifulSoup


def getTitle(q, url, chanID):
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
	q.put((message, chanID))

logging.basicConfig(filename=config.logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)

operational = False
private = False

server = config.server
#server = "port80a.se.quakenet.org"
#channel = "#hightech"
channels = config.channels
nickname = config.nickname

q = Queue.Queue()

irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
irc.settimeout(2)

irc.connect((server, 6667))

logging.info("Connected to server %s", server)


irc.send("USER " + nickname + " " + nickname + " " + nickname + " :Linkbot\n")
irc.send("NICK " + nickname + "\n")
irc.send("PRIVMSG nickserv :NOOPE\r\n")

logging.info("User and nicknames set")

#print "Entering while loop"

urlReg = re.compile(r"(http://[^ ]+|https://[^ ]+)")
channelReg = re.compile(r"(#[^ ]+)")

while 1:
	try:
		message = irc.recv(2040)
		print message
		logging.info("Recieved message: %s", message)
	except Exception, e:
		#print e
		message = ""

	#PingPong
	if message.find("PING") != -1:
		irc.send("PONG " + message.split()[1] + "\r\n")
		logging.debug("PONG")
	#Joining channels
	if message.find("End of /MOTD command.") != -1:
		for i in channels:
			irc.send("JOIN " + i + "\n")
			logging.info("Joined channel %s", i)
		operational = True

	#Ignoring private messages
	if len(message.split())>=3 and message.split()[2].find(nickname) != -1:
		logging.info("Message was private")
		private = True

	if not q.empty():
		print q.qsize()
		while not q.empty():
			t = q.get()
			m = t[0]
			c = channels[t[1]]

			print "sending message " + m.rstrip(os.linesep)
			m = m.rstrip(os.linesep)
			logging.info("Sending message: PRIVMSG %s :%s", c, m)
			#irc.send("PRIVMSG " + channel +" :"+ m.encode('utf8') +" \n")
			irc.send("PRIVMSG " + c +" :"+ m +" \n")

	else:
		if operational and not private:
			url = urlReg.findall(message)
			if url:
				for u in url:
					print "Found link " + u
					chanID = channels.index(channelReg.findall(message)[0])
					logging.info("Found link %s in %s", u, channels[chanID])
					t = threading.Thread(target=getTitle, args=(q, u.rstrip(), chanID))
					t.daemon = True
					t.start()
					#irc.send("PRIVMSG " + channel +" :"+ "Found url: " +u +"\n")
		else:
			private = False
