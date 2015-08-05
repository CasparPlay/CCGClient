#-*- coding: UTF-8 -*-
'''
CCClient.py - A BackToBack client for CasparCG Server. Written by
Md. Rakib Hassan Mullick <rakib.mullick@sysnova.com>.

Copyright (C) 2015, Sysnova Information Systems Ltd.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

This program is written to send commands to CasparCG Server; requests
will be fetched from database. mysql db is used -
	* MySQL-python-1.2.4b4.win32-py2.7 taken from following url -
		http://sourceforge.net/projects/mysql-python
'''

import socket, os, string
import MySQLdb, select, sys
import thread, time, struct, decimal

_FLOAT_DGRAM_LEN = 4

myplaylist = []
buddyplaylist = []
buddyip=''
buddydbname = ''
buddydbpass = ''
buddydbuser = ''
serverip = ''
serverdbname = ''
serverdbpass = ''
serverdbuser = ''
scriptisrunning = 0
nowplaying = ''
logpath = ''
oscsock = 0
OscClientPort = 7250
layerpaused = False
buddynowplaying = ''
isbuddyplayingcommercial = 0
isRecovery = False
sock = 0
cgupdate = 0
isbuddydbrunning = True
logooff = False
cgrunning = False
osct1 = 0.0
osct2 = 0.0
commercialtimelist = []
clearcgstatus = 0
newscoophost=''
newscooppass=''
newscoopuser=''
newscoopdb=''
header = "<?xml version=\"1.0\" encoding=\"utf-16\" standalone=\"yes\"?>\n <NewScrollData>\n"
footer = "</NewScrollData>"

def CreateClient():
		sock = socket.create_connection(('localhost', 5250))
		return sock

def SendToServer(fd, cmd):
	fd.send(cmd)

def ConvertToSec(h, m, s):
	#print "ConvertToSec====>", h,m,s
	second = (int(h)*60*60)+(int(m)*60)+int(s)
	#print second
	return second

def clearCG():
	global sock, cgupdate, clearcgstatus
	if cgupdate == 1:
		cmd = 'cg 1 clear 10\r\n'
		SendToServer(sock, cmd)
		clearcgstatus = 0
		cgupdate = 0

'''
This function basically used to control what to be shown on text scroller. They
are basically distinguished between commercial and non-commercial.
'''
def cgSendCmd(commercial):
	global cgupdate, cgrunning, sock
	
	str = "CG 1 ADD 10 \"AKCESS_CG/Templates/AKCESS\" 1 "
	str = str + "\"<templateData>"
	str = str + "<componentData id=\\"
	str = str + "\"LoadXMLFile\\\">"
	if commercial == 0:
		str = str + "<data id=\\" + "\"text\\\"" +  " value=\\" + "\"C:\\\Intro.axd\\\" />" + "</componentData>"		
	if commercial == 1:
		str = str + "<data id=\\" + "\"text\\\"" +  " value=\\" + "\"C:\\\Commercial.axd\\\" />" + "</componentData>"
	str = str + "<componentData id=\\"
	str = str + "\"LoadLogo\\\">"
	str = str + "<data id=\\" + "\"text\\\"" + " value=\\" + "\"C:/caspar.jpg\\\" />" + "</componentData>"

	str = str + "<componentData id=\\"
	str = str + "\"LoadBG_Strip\\\">"
	str = str + "<data id=\\" + "\"text\\\"" + " value=\\" + "\"C:/BG_Strip.png\\\" />" + "</componentData>"

	str = str + "<componentData id=\\"
	str = str + "\"SetSpeed\\\">"
	str = str + "<data id=\\" + "\"text\\\"" + " value=\\" + "\"3\\\" />" + "</componentData>"
	str = str + "</templateData>" + "\r\n"

	if cgupdate == 1:
		clearCG()
	SendToServer(sock, str)
	cgupdate = 1
	cgrunning = True

def isAscii(s):
    for c in s:
        if c not in string.ascii_letters:
            return False
    return True

def PickString(dgram, idx):
	name = ''
	# we are interested only in ascii characters
	while idx < len(dgram) and (dgram[idx] == ' ' or isAscii(dgram[idx]) == False):
            idx += 1
			
	while idx < len(dgram) and (dgram[idx] != '.' or dgram[idx] != ' ' or dgram[idx] != '\0'):
		name += dgram[idx]
		idx += 1
	return name

def get_float(dgram, start_index):
  """Get a 32-bit big-endian IEEE 754 floating point number from the datagram.
  Args:
    dgram: A datagram packet.
    start_index: An index where the float starts in the datagram.

  Returns:
    A tuple containing the float and the new end index.

  Raises:
    ParseError if the datagram could not be parsed.
  """
  try:
    if len(dgram[start_index:]) < _FLOAT_DGRAM_LEN:
      # Noticed that Reaktor doesn't send the last bunch of \x00 needed to make
      # the float representation complete in some cases, thus we pad here to
      # account for that.
      dgram = dgram + b'\x00' * (_FLOAT_DGRAM_LEN - len(dgram[start_index:]))
    return (
        struct.unpack('>f',
                      dgram[start_index:start_index + _FLOAT_DGRAM_LEN])[0],
        start_index + _FLOAT_DGRAM_LEN)
  except (struct.error, TypeError) as e:
    raise ParseError('Could not parse datagram %s' % e)

def BuddyOscMsg(packet, filename):
	global nowplaying, layerpaused
	ispaused = False
	# a Typical pattern is like /channel/1/stage/layer/10/file/time ,ff
	tret = []
	ret = packet.find('10/file/path')
	if ret != -1:
		ret = packet.find(',s', ret)
		if ret == -1:
			return tret
		ret += 4
		tmpplaying = PickString(packet, ret)
		#print "tmpplaying, filename", tmpplaying, filename
		tmpplaying = tmpplaying.lower()
		filename = filename.lower()
		if tmpplaying.find(filename) == -1:
			return tret
		#print "Looking for ", filename
		ret = packet.find('file/time')
		if ret != -1:
			ret = packet.find(',ff', ret)
			if ret == -1:
				return tret
			ret += 4
			fval, index = get_float(packet, ret)
			fval2, newindex = get_float(packet, index)
			tret.append(fval)
			tret.append(fval2)
			#print "%s is played %f of %f" % (tmpplaying, fval, fval2)
			return tret

# format h:m:s '12:12:01'
# ct currenttime, st starttime
def WaitTime(ct, st):
	#print ct, st
	try:
		ch,cm,cs = ct.split(':')
	except:
		return
	try:
		sh,sm,ss = st.split(':')
	except:
		return
	
	dh = int(sh) - int(ch)
	dm = int(sm) - int(cm)
	ds = int(ss) - int(cs)
	totals = 0
	if dh > 0:
		totals += dh * 60
	if dm > 0:
		totals += dm * 60
	totals = totals + ds
	#print totals
	return totals

def UpdateBuddyDb(name, state):
	buddydb = MySQLdb.connect(buddyip, buddydbuser, buddydbpass, buddydbname)
	buddycursor = buddydb.cursor()
	sql = "UPDATE playlist SET state='%s' where name='%s'" % (state, name)
	try:
		buddycursor.execute(sql)
		buddydb.commit()
	except:
		print "DB update failed"
	buddydb.close()

'''
WARNING!!! All the playlist items needs to have an unique name.
A typical name should contain clipname with name-time-date of playout.
Example - clip1-14-10-03-06-2015
'''
def UpdateDb(name, id, state):
	global isbuddydbrunning
	db = MySQLdb.connect(serverip, serverdbuser, serverdbpass, serverdbname)
	cursor = db.cursor()
	sql = "UPDATE playlist SET state='%s' where name='%s' and id='%s'" % (state, name, id)
	try:
		cursor.execute(sql)
		db.commit()
		sql = ''
		sql = "UPDATE playlist SET pushtime=now() WHERE name='%s' AND id='%s'" % (name, id)
		cursor.execute(sql)
		db.commit()
	except:
		print "DB update failed"
	db.close()
	
	try:
		if isbuddydbrunning == True:
			UpdateBuddyDb(name, state)
	except:
		pass

'''
OSCGetSleepTime - try to figure out %name's playout time via OSC
%returns -1 on failure
'''
def OSCGetSleepTime(name):
	global oscsock
	count = 10
	#print "Into OSCGetSleepTime"
	
	while True:
		data, addr = oscsock.recvfrom(512)
		if addr == buddyip:
			continue
		timeval = BuddyOscMsg(data, name)
		#print "timeval", timeval
		if timeval == None:
			continue
		try:
			if len(timeval) == 0:
				continue
			diff = timeval[1] - timeval[0]
			return diff
		except:
			return -1.0

def PrepareBreakScroller():
	global commercialtimelist
	try:
		tym = commercialtimelist.pop(len(commercialtimelist)-1).split('|')
	except:
		tym = []
		pass
	msg1 = "<?xml version=\"1.0\" encoding=\"utf-16\" standalone=\"yes\"?>"
	msg2 = "<NewScrollData> <ScrollData> <Story>"
	msg3 = "ফিরছি %s সেকেন্ড পর, আমাদের সথেই থাকুন." % tym[1]
	#msg3 = "We will be back after %s seconds, Stay With Us." % tym[1]
	msg4 = "</Story> </ScrollData> </NewScrollData>"
	msg = msg1 + msg2 + msg3 + msg4
	f = open("C:\\Commercial.axd","w")
	f.write(msg)
	f.close()

def playoutHandler(val):
	global scriptisrunning, isRecovery, sock, logooff, cgrunning, isbuddyplayingcommercial, osct1, osct2, commercialtimelist
	prevclip = ''
	try:
		sock = CreateClient()
	except:
		print "Failed to Connect To CasparCG Server, Make Sure Server is Running"
		return
	
	SendToServer(sock, "version\r\n")
	data = sock.recv(20)
	print data
	sleeptime = 0
	
	''' The following is for recovery, ie. catching up with where buddy is running'''
	if val > 0.0:
		isRecovery = True
		st = val[0] - int(val[0])
		st = st/.04
		print "seek into frame", (val[1] - val[0])
		osct2 = time.time()
		td = (osct2 - osct1)/.04
		seekt = (int(val[0]) * 25) + st + td + 12
		pcmd = "loadbg 1-10 %s seek %d auto\r\n" % (buddynowplaying, int(seekt))
		SendToServer(sock, pcmd)
		if isbuddyplayingcommercial == '0':
			SendToServer(sock, "loadbg 1-11 logo auto\r\n")
		else:
			logooff = True

		time.sleep(int(val[1]-val[0]))
		# now read data from the file and starts playout
		# loadbg 1-10 tomnje seek 251 length 751 auto
		# name|id|timecode|starttime|seek|length
		# TODO: Handle commercial, put commercial and programs on different layers
		# needs to handle properly

	playlistlen = len(myplaylist)
	
	while True:
		try:
			currlist = myplaylist.pop(0)
		except:
			FetchPlayList(1)
			if len(myplaylist) == 0:
				print "Nothing to be played, retrying within 5 seconds..."
				time.sleep(5)
			else:
				CommercialTimes()
			continue
		#name, id, tlength, starttime, seek, length, commercial = myplaylist[i].split("|")
		name, id, tlength, starttime, seek, length, commercial = currlist.split("|")
		hour, min, sec, msec = tlength.split(":")
		
		didshowcg = 0
		if scriptisrunning == 0 and isRecovery == False:
			t1 = time.time()
			currtime = time.ctime()
			currtime = currtime.split(" ")
			currtime = currtime[3]
			print currtime, starttime
			starttime = starttime
			diff = WaitTime(currtime, starttime)
			t2 = time.time()
			#print "Waiting time", diff
			scriptisrunning = 1
			if diff > 0:
				time.sleep(diff-(t2-t1))
			pcmd = ''
			pcmd = "loadbg 1-10 %s auto\r\n" % (name)
			if commercial == '1' and logooff == False:
				SendToServer(sock, "clear 1-11\r\n")
				logooff = True
				if cgrunning == True:
					clearCG()
					cgrunning = False
			if commercial == '0' and logooff == False:
				SendToServer(sock, "loadbg 1-11 logo auto\r\n")
				logooff = False
			SendToServer(sock, pcmd)
			UpdateDb(name, id, '1')
			sleeptime = OSCGetSleepTime(name) #ConvertToSec(hour, min, sec)
			#print sleeptime
			#entry = myplaylist[i+1].split('|')
			try:
				entry = myplaylist[1].split('|')
				if entry[6] == '1' and sleeptime > 10:
					#print "NExt video is commercial"
					time.sleep(sleeptime-10)
					PrepareBreakScroller()
					cgSendCmd(1)
					if len(commercialtimelist) == 0:
						CommercialTimes()
					cgrunning = True
					didshowcg = 1
			except:
				pass
			if didshowcg == 0:
				time.sleep(sleeptime-1)
			else:
				time.sleep(5)
			UpdateDb(name, id, '2')
			# myplaylist.pop(i)
		else:
			pcmd = ''
			## TODO: get sleeptime via OSC OSCGetSleepTime(name)
			pcmd = "loadbg 1-10 %s auto\r\n" % (name)
			SendToServer(sock, pcmd)
			sleeptime = OSCGetSleepTime(name) #ConvertToSec(hour, min, sec)
			UpdateDb(name, id, '1')
			if commercial == '0' and logooff == True:
				SendToServer(sock, "loadbg 1-11 logo auto\r\n")
				logooff = False
				cgSendCmd(0)
			if cgrunning == True and commercial == '1':
				clearCG()
				cgrunning = False
			if commercial == '1' and logooff == False:
				SendToServer(sock, "clear 1-11\r\n")
				logooff = True
				didshowcg = 0
			if len(myplaylist) > 0:
				#entry = myplaylist[1].split('|')
				entry = myplaylist[0].split('|')
				#print "entry is:", entry[0]
				if entry[6] == '1' and sleeptime > 10 and commercial == '0':
					#print "NExt video is commercial"
					time.sleep(sleeptime-10)
					PrepareBreakScroller()
					cgSendCmd(1)
					cgrunning = True
					didshowcg = 1
					if len(commercialtimelist) == 0:
						CommercialTimes()
				else:
					if didshowcg == 0:
						time.sleep(sleeptime-1)
					else:
						time.sleep(5)
			else:
				if sleeptime > 2:
					time.sleep(sleeptime-1)
			UpdateDb(name, id, '2')
	sock.close()
	
'''
	* GetBuddyIP, db, credentials
	* make connection
	* fetch list from db => id,name,starttime
	* buddyplaylist[], keep all the program list in it
	TODO: Also make sure that this DB and buddy DB are sync.
'''
def CheckBuddyPlayList():
	global isbuddydbrunning
	try:
		db = MySQLdb.connect(buddyip, buddydbuser, buddydbpass, buddydbname)
		cursor = db.cursor()
		sql = "SELECT name,id,timecode,starttime,seek,length,commercial FROM playlist WHERE state='0'"
		print "connected to buddy db"
		try:
			cursor.execute(sql)
			results = cursor.fetchall()
			print "Got Results of len: %d" % len(results)
			for r in results:
				global myplaylist
				#print r[0], r[1]
				tmp = r[0] +'|'+ str(r[1]) + '|' + str(r[2]) + '|' + str(r[3]) + '|' + str(r[4]) + '|' + str(r[5]) + '|' + str(r[6])
				#print tmp
				myplaylist.append(tmp)
		except:
			isbuddydbrunning = False
			print "Failed To FetchPlayList From BUDDY DB"
		print "After myplaylist update length => ", len(myplaylist)
		db.close()
	except:
		isbuddydbrunning = False
		print "Make Sure Buddy DB is on"
		pass
'''
	* GetCurrentTime
	* Find all the programs yet to be scheduled later than currenttime
	* make sure this playlist conttains all the video list from buddyplaylist[]
'''
def MergePlayList():
	global myplaylist
	newplaylist = myplaylist
	times = len(myplaylist)
	print "into merging", len(myplaylist)
	for i in range(0, times):
		#print myplaylist[i]
		#tmpname, tmpid, tmptlength, tmpstarttime, tmpseek, tmplength = myplaylist[i].split("|")
		try:
			tmplist = myplaylist[i].split('|')
			#print "into merging ", myplaylist[i]
			for j in range(0, times):
				if i == j:
					continue
				#name, id, tlength, starttime, seek, length = myplaylist[j].split('|')
				try:
					nlist = myplaylist[j].split('|')
					if tmplist[0] == nlist[0]: # and tmplist[1] == nlist[1]:
						#remove the entry
						myplaylist.remove(myplaylist[j])
						times = times - 1
						break
				except:
					pass
		except:
			pass
	print "after merging %d %s" % (len(myplaylist),myplaylist)

def AddTime(src, dst):
	print "src =>", src
	print "dst =>", dst
	tmpsrc = src.split(':')
	tmpdst = dst.split(':')
	totals = 0
	tmp = int(tmpsrc[3]) +  int(tmpdst[3])
	totalf = tmp % 25
	totals = int(tmp)/25
	totals = int(tmpsrc[2]) + int(tmpdst[2]) + totals
	totalm = totals/60
	totals = totals%60
	totalm = int(tmpsrc[1]) + int(tmpdst[1]) + totalm
	totalh = int(tmpsrc[0]) + int(tmpdst[0])
	ret = str(totalh)+':'+str(totalm)+':'+str(totals)+':'+'00'
	#print "AddTime ==> ", ret
	return ret

def CommercialTimes():
	global myplaylist, commercialtimelist
	commercialtimelist = []
	length = len(myplaylist)
	index = 0
	prev = 0
	total = '00:00:00:00'
	i = 0
	while True:
		if i >= length:
			break
		varlist = myplaylist[i].split('|')
		if varlist[6] == '1':
			total = varlist[2]
			i = i + 1
			for t in range(i, length):
				tlist = myplaylist[t].split('|')
				if tlist[6] == '1':
					total = AddTime(total, tlist[2])
				else:
					i = t+1
					break
			sec = total.split(':')
			sec = ConvertToSec(int(sec[0]),int(sec[1]),int(sec[2]))
			entry = varlist[0] + '|' + str(sec)
			commercialtimelist.append(entry)
			total = '00:00:00:00'
		else:
			i = i + 1
	#print "commercial list = >", commercialtimelist
	commercialtimelist.reverse()

'''
Here we'll be checking the buddy's playlist and will compare it with ours
if any mismatch found playlist will be merged
%skipbuddy - indicates whether we should check buddy server
'''
def FetchPlayList(skipbuddy):
	global myplaylist, isbuddydbrunning
	db = MySQLdb.connect(serverip,serverdbuser,serverdbpass,serverdbname)
	cursor = db.cursor()
	# TODO: select only name,id,timecode,commercial flags
	sql = "SELECT name, id, timecode, starttime, seek, length, commercial FROM playlist WHERE state='0'"
	try:
		cursor.execute(sql)
		results = cursor.fetchall()
		#print "Got Results of len: %d" % len(results)
		for r in results:
			tmp = r[0] + '|' + str(r[1]) + '|' + str(r[2]) + '|' + str(r[3]) + '|' + str(r[4]) + '|' + str(r[5]) + '|' + str(r[6])
			#print tmp
			myplaylist.append(tmp)
	except:
		print "Failed To FetchPlayList From DB"
		pass
	db.close()
	print " myplaylist len: %d, %s" % (len(myplaylist), myplaylist)
	if skipbuddy == 0:
		CheckBuddyPlayList()
		if isbuddydbrunning == True:
			MergePlayList()

'''
createtable - create new tables required by the script
If already exist, skip silently, for now hardcode the
username, pass, dbname
'''
def createtable():
	#print "serverparam %s %s %s %s" % (serverip, serverdbname, serverdbpass, serverdbuser)
	db = MySQLdb.connect(serverip, serverdbuser, serverdbpass, serverdbname)
	cursor = db.cursor()
	sql = "CREATE TABLE casparcg (vname CHAR(30) NOT NULL, vlength CHAR(15) NOT NULL)"
	try:
		cursor.execute(sql)
		db.commit()
	except:
		db.rollback()
		print "Table already created"
	db.close()
	

def createDB():
	db = MySQLdb.connect(serverip, serverdbuser, serverdbpass, serverdbname)
	cursor = db.cursor()
	sql = 'CREATE database casparcg'
	try:
		cursor.execute(sql)
		db.commit()
	except:
		db.rollback()
		print "DB already created"
	db.close()

def initdb():
	createtable()

def CreateConFile():
	buf = []
	buf.append("[General]")
	buf.append("buddyip=")
	buf.append("buddydbname=")
	buf.append("buddydbuser=")
	buf.append("buddydbpass=")
	buf.append("serverip=")
	buf.append("serverdbname=")
	buf.append("serverdbuser=")
	buf.append("serverdbpass=")
	buf.append("logpath=")
	
	try:
		p = os.environ.get('LOCALAPPDATA')
		print p
		p = p + "\\CSClient"
		try:
			os.mkdir(p)
			p = p + "\\csclient.ini"
			cmd = "copy nul %s > nul" % p
			try:
				os.system(cmd)
				for i in range(0, len(buf)):
					cmd = "echo %s >> %s" %(buf[i], p)
					os.system(cmd)
			except:
				print "failed to create ini file"
		except:
			print "Failed to create directory"
	except:
		print "Failed to create dir"

def ReadConFile():
	fpath = os.environ.get('LOCALAPPDATA')
	p = fpath + "\\CSClient\\csclient.ini"
	confile = open(p, 'r')
	try:
		#print confile
		confile.seek(0)
		while True:
			ret = confile.readline()
			#print ret
			if ret == '':
				break
			if ret == '[General]':
				print ret
				continue
			array = ret.split('=')
			if array[0] == 'buddyip':
				global buddyip
				buddyip = array[1].rstrip('\n')
				#print array[1]
				continue
			if array[0] == 'buddydbname':
				global buddydbname
				buddydbname = array[1].rstrip('\n')
				continue
			if array[0] == 'buddydbuser':
				global buddydbuser
				buddydbuser = array[1].rstrip('\n')
				continue
			if array[0] == 'buddydbpass':
				global buddydbpass
				buddydbpass = array[1].rstrip('\n')
				continue
			if array[0] == 'serverip':
				global serverip
				serverip = array[1].rstrip('\n')
				continue
			if array[0] == 'serverdbname':
				global serverdbname
				serverdbname = array[1].rstrip('\n')
				print serverdbname
				continue
			if array[0] == 'serverdbpass':
				global serverdbpass
				serverdbpass = array[1].rstrip('\n')
				print serverdbpass
				continue
			if array[0] == 'serverdbuser':
				global serverdbuser
				serverdbuser = array[1].rstrip('\n')
				print serverdbuser
				continue
			if array[0] == 'logpath':
				global logpath
				logpath = array[1].rstrip('\n')
				print logpath
				continue
			if array[0] == 'newscoophost':
				global newscoophost
				newscoophost = array[1].rstrip('\n')
				continue
			if array[0] == 'newscooppass':
				global newscooppass
				newscooppass = array[1].rstrip('\n')
				print newscooppass
				continue
			if array[0] == 'newscoopuser':
				global newscoopuser
				newscoopuser = array[1].rstrip('\n')
				print newscoopuser
				continue
			if array[0] == 'newscoopdb':
				global newscoopdb
				newscoopdb = array[1].rstrip('\n')
				print newscoopdb
				continue
		confile.close()
	except:
		print "Failed to read confile"
	confile.close()

def initCSClient():
	CreateConFile()
	ReadConFile()

def GetBuddyNowPlaying():
	db = MySQLdb.connect(serverip, serverdbuser, serverdbpass, serverdbname)
	cursor = db.cursor()
	sql = "SELECT name,commercial FROM playlist WHERE state='1'"
	results = ''
	try:
		cursor.execute(sql)
		results = cursor.fetchall()
		for r in results:
			tmp = r[0] + '|' + r[1]
			return tmp
	except:
		pass
	db.close()
	return results

def CreateOscSocket():
	global oscsock
	oscsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	oscsock.bind(('', OscClientPort))

'''
This function basically detects whether we're on recovery phase or initializing for the first time.
A tentative technique is to listen for OSC messages, try to listen for few seconds to get an idea of
when to trigger.
'''
def isRecoveryStartup():
	global buddynowplaying, oscsock, isbuddyplayingcommercial, isbuddydbrunning
	CreateOscSocket()
	if isbuddydbrunning == False:
		return 0.0
	tmp = GetBuddyNowPlaying()
	#print "*************************", buddynowplaying
	if len(tmp) == 0:
		return 0.0
	buddynowplaying = tmp
	if buddynowplaying == '':
		#print "*******************Not Recovery Startup"
		return 0.0
	#print "=========>>>buddy is playing", buddynowplaying
	#print "Waiting for OSC MSG"
	buddynowplaying, isbuddyplayingcommercial = buddynowplaying.split('|')
	count = 10
	while count > 0:
		data, addr = oscsock.recvfrom(512)
		#print addr, data
		if addr == serverip:
			continue
		# take only buddyOSC messages
		timeval = BuddyOscMsg(data, buddynowplaying)
		try:
			if len(timeval) == 0:
				continue
			print "Played %f of %f seconds" % (timeval[0], timeval[1])
			count -= 1
			diff = float(timeval[1]) - float(timeval[0])
			return timeval
		except:
			pass
		if count == 0:
			return 0.0

def CGWriteToFile(news, skipcmd=0):
	global sock, cgupdate, cgrunning
	'''CG 1 ADD 10 "AKCESS_CG/Templates/AKCESS" 1 "<templateData><componentData id=\"LoadXMLFile\"><data id=\"text\" value=\"C:\\Intro.axd\" /></componentData><componentData id=\"LoadLogo\"><data id=\"text\" value=\"C:/caspar.jpg\" /></componentData><componentData id=\"LoadBG_Strip\"><data id=\"text\" value=\"C:/BG_Strip.png\" /></componentData><componentData id=\"SetSpeed\"><data id=\"text\" value=\"5\" /></componentData><componentData id=\"SetFontSize\"><data id=\"text\" value=\"50\" /></componentData></templateData>\r\n
'''
	if cgupdate == 1:
		SendToServer(sock, "cg 1 remove 10\r\n")

	f = open("C:\\Intro.axd", "w")
	f.write(news)
	f.close()
	if skipcmd == 0:
		cgSendCmd(0)
		cgrunning = True
	
def putSquzee():
	global sock
	SendToServer(sock, "MIXER 1-10 FILL .15 0 .85 .80\r\n")

'''
%CG_Handler - this thread is dedicated for handling request from client.
This will use the internally deployed flash script and will put text on
scroll or other various stuffs.
'''
def CG_Handler():
	global cgrunning, clearcgstatus
	cgsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	cgsock.setblocking(0)
	cgsock.bind(('', 8000))
	input = [cgsock]
	while True:
		inputready, outputready, exceptready = select.select(input,[],[])
		for s in inputready:
			if s == cgsock:
				cgdata, addr = cgsock.recvfrom(65565)
				if len(cgdata) == 6:
					if cgdata == 'squzee':
						putSquzee()
						clearcgstatus = 1
						continue
				if len(cgdata) == 8:
					if cgdata == 'cgstatus':
						cgsock.sendto(str(clearcgstatus), addr)
						continue
				if len(cgdata) == 7:
					if cgdata == 'clearcg':
						cgrunning = False
						clearCG()
						continue
				print "Data %s recvfrom %s" % (cgdata, addr)
				CGWriteToFile(cgdata)

# Update own server playlist state, when we are sure that we are
# on recovery state, that means we could be crashed in the middle of
# something, so make sure we don't have anything at state='1'
def UpdateMyDbState():
	db = MySQLdb.connect(serverip,serverdbuser,serverdbpass,serverdbname)
	cursor = db.cursor()
	sql = "UPDATE playlist SET state='2' WHERE state='1'"
	results = ''
	try:
		cursor.execute(sql)
	except:
		pass
	db.close()

def GenerateFilename(fname):
	print fname
	prefix='caspar_'
	'''t = time.localtime()
	p = str(t.tm_year)
	if len(str(t.tm_mon)) > 1:
		p = p + '-' + str(t.tm_mon)
	else:
		p = p + '-0' + str(t.tm_mon)
	if len(str(t.tm_mday)) > 1:
		p = p + '-' + str(t.tm_mday)
	else:
		p = p + '-0' + str(t.tm_mday)'''
	prefix += fname + ".log"
	#print "GenerateFilename ==>", prefix
	return prefix

def parseMessage(logf):
	buf = []
	try:
		f = open(logf, 'r')
	except:
		print "Unable to open file. Makesure filename is okay"
		return buf
	while True:
		t = f.readline()
		if t == '':
			break
		m = t.find('transition[empty=>ffmpeg[')
		if m > 0:
			m += 25
			m = t.find('Uninitialized.', m)
			if m > 0:
				buf.append(t)
				continue
		m = t.find(' transition[ffmpeg[')
		if m > 0:
			m += 18
			m = t.find('Uninitialized.', m)
			if m > 0:
				buf.append(t)
				continue
	f.close()
	return buf

def GenerateReport(fdate):
	global logpath
	preparebuf = []
	path = logpath #"D:\CasparCG\caspercg server\Server\log"
	#path = "log"
	fname = GenerateFilename(fdate)
	path = path + '\\' + fname
	#print "Invoking Generate Report => ", path
	rbuf = parseMessage(path)
	if len(rbuf) == 0:
		#print "Nothing to Parse"
		return preparebuf

	for i in range(0,len(rbuf)):
		l = rbuf[i].split(' ')
		line = l[1].strip(']') + '|' + l[7].split('=>')[1].strip('ffmpeg').strip('[').split('|')[0]+'\r\n'
		preparebuf.append(line)
		#print "%s added" % (line)
	return preparebuf
	
def GetDays(fdate, tdate):
	print fdate, tdate
	days = 0
	fy, fm, fd = fdate.split("-")
	ty, tm, td = tdate.split("-")
	if int(fy) > int(ty):
		days = (int(fy) - int(ty)) * 365
	if int(ty) < int(fy):
		days = (int(ty) - int(fy)) * 365

	if int(fm) > int(tm):
		days = days + (int(fm) - int(tm)) * 30
	if int(fm) < int(tm):
		days = days + (int(fm) - int(tm)) * 30
		
	if int(fd) > int(td):
		days = days + int(fd) - int(td)
	if int(fd) < int(td):
		days = days + int(td) - int(fd)
	return days

'''def NextDate(fdate):
	ny = 0
	nm = 0
	nd = 0
	y, m, d = fdate.split("-")
	if int(m) % 2 == 0:
		if int(m) == 2:
			if int(m) > 28:
				nm = int(m) + 1
	else:
		if int(d) > 31:
			nm = int(m) + 1
'''
def ReportHandler():
	reportbuf = []
	reportsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	reportsock.setblocking(0)
	reportsock.bind(('', 9000))
	reportsock.listen(5)
	input = [reportsock]
	output = [reportsock]
	print "ReportHandler Ready..."

	while True:
		inputready,outputready,exceptready = select.select(input,output,[])
		for s in inputready:
			if s == reportsock:
				connection, client_addr = s.accept()
				connection.setblocking(0)
				input.append(connection)
			else:
				reportcmd = s.recv(1024)
				ret = reportcmd.find("GETREPORT")
				if ret != -1:
					tmpr = reportcmd.strip()
					tmpr = tmpr.split(' ')
					fromdate, todate = tmpr[1].split(":")
					days = GetDays(fromdate, todate)
					print "Days: ", days
					for x in range(0, days+1):
						reportbuf = GenerateReport(fromdate)
						if len(reportbuf) > 0:
							sizeb = len(reportbuf)
							for i in range(0, sizeb):
								item = reportbuf.pop()
								# we'll be blocking here, nevermind, we dont care. we'll be done when it's finished
								s.send(item)
								print "sending to client", item
				else:
					# We are done now, we're not supposed to get any commands
					s.close()
					input.remove(s)

'''
%feeds - list containing all the news headlines.
'''
def PrepareNews(feeds):
	import codecs
	global header, footer
	f = open("C:\\Intro.axd", "w")
	head = unicode(header)
	f.write(header)
	for i in range(0, len(feeds)):
		f.write("<ScrollData>\n<Story>\n" + feeds[i] + "</Story>\n</ScrollData>\n")
	f.write(footer)
	f.close()
	cgSendCmd(0)

def newsFetcher():
	global newscoopdb, newscoophost, newscooppass, newscoopuser
	time.sleep(10)	# allow main thread to initialize, otherwise client socket wont be available
	
	while True:
		db = MySQLdb.connect(newscoophost, newscoopuser, newscooppass, newscoopdb, charset='utf8', use_unicode=True)
		cursor = db.cursor()
		tmp = time.localtime()
		fdate = str(tmp.tm_year) + '-' + str(tmp.tm_mon) + '-' + str(tmp.tm_mday) + ' ' + '00:00:00'
		tdate = str(tmp.tm_year) + '-' + str(tmp.tm_mon) + '-' + str(tmp.tm_mday) + ' ' + '23:59:59'
		sql = "SELECT Name FROM Articles WHERE PublishDate BETWEEN " + '\'' + fdate + '\'' + ' AND ' + '\'' + tdate + '\''
		print sql
		newsfeeds = []
		results = ''
		try:
			cursor.execute(sql)
			results = cursor.fetchall()
			print "Got Results of len: %d" % len(results)
			tmp = ""
			for r in results:
				tmp = r[0].encode("utf-8", "replace")
				newsfeeds.append(tmp)
		except:
			pass
		db.close()
		PrepareNews(newsfeeds)
		time.sleep(300)	# change later

if __name__ == "__main__":
	initCSClient()
	initdb()
	FetchPlayList(0)
	osct1 = time.time()
	ret = isRecoveryStartup()
	if ret != 0.0:
		UpdateMyDbState()
	CommercialTimes()
	thread.start_new_thread(CG_Handler,())
	thread.start_new_thread(ReportHandler,())
	thread.start_new_thread(newsFetcher,())
	playoutHandler(ret)
