# CCGClient


1. OVERVIEW:
	CCGClient is designed to work as client for CasparCG playout server and a server for the modified
Sysnova CasparCG Client. Unlink, other clients, CCGClient driven by MySQL database and this client will
work with multiple CasparCG server also. To do that it needs to be configured properly ie. the redundant 
server should be configure as buddy server. As a prerequisite MySQL db needs to be installed on the server.
This client assumes that some other client (our modified CasparCG Client) will create a playlist and will
push it on the server. Then, even if that client isn't available the CasparCG server will continue it's
playout as it is. In this way, CCGClient deals with client failure and with buddy server configured it make
sure it's also provide server backup.

2. Prerequisite:
	The following dependency is required for the script to run.
			a/ Python-2.7
			b/ MySQL-python 2.7 (http://sourceforge.net/projects/mysql-python)
			c/ MySQL 5.6 (tested with this version)

3. Sample Configuration:
	A sample configuration is like below. buddyip is the ipaddress of the redundant server used for
backup, buddydbname is the database name created by the script, buddydbuser and buddydbpass are the
username and password of buddy database, respectively. Likewise - serverip, serverdbname, serverdbpass,
serverdbuser are host server ip, database name, database password and database username, respectively.

		[General]
		buddyip=192.168.152.8
		buddydbname=casparcg
		buddydbuser=dbuser
		buddydbpass=password
		serverip=127.0.0.1
		serverdbname=casparcg
		serverdbuser=dbuser
		serverdbpass=password
		logpath=casparcgserver\log

	All the above fields are required to put into csclient.ini file and should be put on CSclient folder
	under AppData\Local directory. Also make sure to keep the tv logo file as name "logo" under media
	directory of CasparCG server.

4. CasparCG Configuration:
	If you want to make sure that after a system failure, if you want to make it available from where
the other server is running, then on CasparCG configuration "Predifined Clients" needs to be configured
properly. On the main server, buddy server IP, Port no 7250 (fixed as of now) needs to be configured as
Predifined Client and vice versa for the buddy server.

5. Recovery Time:
	To figure out the difference between two servers we collected few tentative numbers. On 12 runs, scripts
shows that on an average it's 0.30 sec lag between videos; worst cast was 1.5 sec gap between playouts on
best cast we found near about 0.1 sec lag.

6. MySQL Database preparation:
	Script will create a CasparCG database if already not created. schema.txt file contains the table schema
which should be created after then.

7. Newscoop Integration:
	Newscoop is a free and open source multilingual content management system for news websites. CCGClient is
capable of fetching news headlines from newscoop database and can use it as text scroller.

TODO:	a/ Database table creation automation.
		b/ Various code cleanup is also required.
