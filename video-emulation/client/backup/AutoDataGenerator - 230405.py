import subprocess
import argparse
import numpy as np
from math import factorial, exp
import time, sys
import random
import paramiko
import select
from threading import Thread
import requests
# import client_restartPlayer
if __name__ == "__main__" or __name__ == "AutoDataGenerator":
	import clientConfig
	import player_generator
	import remoteHostClientConfig
	import remoteHostHandler
else:
	from . import clientConfig
	from . import player_generator
	from . import remoteHostClientConfig
	from . import remoteHostHandler

IP_LIST = clientConfig.clientIPList
REMOTE_IP_LIST = remoteHostClientConfig.clientIPList
TOTAL_IP_LIST = IP_LIST + REMOTE_IP_LIST

CLIENT_NAME = clientConfig.clientHostName

class AutoDataGeneratorOptions:
	def __init__(self):
		##############################################
			# Player Generator Options #
		self.NUM_Of_PLAYER = 0
		self.REMOTE_NUM_OF_PLAYER = 1
		self.NUM_OF_TOTAL_PLAYER = self.NUM_Of_PLAYER + self.REMOTE_NUM_OF_PLAYER

		self.VIDEO_RUNNING_TIME = 80 # unit is second
		self.PLAYER_CATEGORY = "firefox" # or "firefox" "google-chrome-stable"

		self.MSERVER_URL = "http://192.168.122.2:8088" # static URL
		self.MSERVER_URL_FOR_REMOTE_HOST = remoteHostClientConfig.mserverURL
		self.CSERVER_URL = "http://192.168.122.3:8888" # static URL
		self.CSERVER_URL_FOR_REMOTE_HOST = remoteHostClientConfig.cserverURL
		self.RSERVER_URL = "http://192.168.122.3:8889"
		self.RSERVER_URL_FOR_REMOTE_HOST = remoteHostClientConfig.rserverURL
		self.BUFFER_TIME = 30 # unit is second
		self.IS_ABR = "true" # or "false"
		self.QUALITY_QUERY_INTERVAL = 3000 # unit is milisecond
		self.SEND_MONITORING_INTERVAL = 2500 # unit is milisecond
		self.SNAPSHOT_INTERVAL = 5000 # unit is milisecond
		self.ABR_STRATEGY = "Dynamic" # or "BOLA" | "L2A" | "LoLP" | "Throughput"

		###############################################
				# VM OPTION #
		self.MAX_PLAYER_PER_CLIENT = 2
		###############################################
				# Auto OPTION #
		self.INCOMMING_TIME = 5
		self.OUTCOMMING_TIME = 5

# def reboot_client(client_ip=None):
# 	# if client_name is None:
# 	# 	for cn in CLIENT_NAME:
# 	# 		print(log_string(f'Reboot client: {cn}'))
# 	# 		subprocess.run(['virsh', 'reboot', cn])
# 	# 		time.sleep(8)

# 	# 	print(log_string('All clients are reset'))
# 	# else:
# 	# 	cn = client_name
# 	# 	print(log_string(f'The client {cn} is reset'))
# 	# 	subprocess.run(['virsh', 'reset', cn])
# 	# 	print(log_string(f'The client {cn} is reset completed'))

# 	if client_ip is None:
# 		for ip in IP_LIST:
# 			print(log_string(f'Reboot client: {ip}'))
# 			client_restartPlayer.restartPlayerWithSSH(ip)
# 			time.sleep(8)

# 		print(log_string('All clients are reset'))
# 	else:
# 		ip = client_ip
# 		print(log_string(f'The client {ip} is reset'))
# 		client_restartPlayer.restartPlayerWithSSH(ip)
# 		print(log_string(f'The client {ip} is reset completed'))

def log_string(str):
	log = '\033[95m' + str + '\033[0m'
	return log


# the 5 clients are comming in 30s. then, 1 second -> 1/6 client is comming per a second.
# so, the lamb is 1/6
def poison_dist(comingTime=30, seed=1000, clientNum=5):
	lamb = clientNum / comingTime
	np.random.seed(seed=seed)
	pd = np.random.poisson(lam=lamb, size=comingTime)
	
	return pd

def checkClientRuntime(poison_dist, comingTime, clientNum):
	pd = poison_dist[:comingTime]
	time_slot = []
	current_client_num = 0

	for i in range(len(pd)):
		if pd[i] == 0:
			continue
		current_client_num += pd[i]
		for j in range(pd[i]):
			if len(time_slot) >= clientNum:
				break
			time_slot.append(i)

		if current_client_num >= clientNum:
			break
	
	if current_client_num < clientNum:
		add_num = clientNum - len(time_slot)
		for i in range(add_num):
			time_slot.append(comingTime-1)

	return time_slot

def run_server(isRunning, isTerminated):
#	ssh = paramiko.SSHClient()
#	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
#	ssh.connect("192.168.0.2", username="wins", password="winslab")
#	stdin, stdout, stderr = ssh.exec_command("python3 server/server.py", get_pty=True)
#	lines = stdout.readlines()
#	print(lines)

	tp = paramiko.Transport(("192.168.122.3", 22)) # CSERVER IP
	tp.connect(username='wins', password='winslab')

	channel = tp.open_session()
	channel.get_pty()
	channel.set_combine_stderr(1)
	channel.exec_command("cd cserver && python3 server_flask.py")
	while isRunning[0]:
		if channel.exit_status_ready():
			if channel.recv_ready():
				break
		output = channel.recv(1024).decode(sys.stdout.encoding)
		sys.stdout.write(output)

		if "[PlayerHandler] call __del__" in output:
			isRunning[0] = False

	print(log_string("Channel closing"))
	channel.close()

	isTerminated[0] = True

def close_server():
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	ssh.connect("192.168.122.3", username="wins", password="winslab")

	stdin, stdout, stderr = ssh.exec_command("ps -ax | grep server_flask.py ")
	lines = stdout.readlines()
	for i in range(len(lines)):
		if 'python3' in lines[i]:
			if 'Ssl' in lines[i]:
				pid = lines[i].split()[0]
	print(log_string(f'current server.py pid is {pid}'))

	stdin, stdout, stderr = ssh.exec_command("kill -2 " + pid)

	##
	# stdin, stdout, stderr = ssh.exec_command("ps -ax | grep server.py ")
	# for line in stdout.readlines():
	# 	print(log_string(line))
	##

	print(log_string("Server closed"))

def main(episode_num, Abr=False, bufferLevel=30, withoutImg=False):
	clientNum=5
	wait_time=80
	incomingTime=30
	outcomingTime=30

	# Abr = False
	# bufferLevel = 30

	print(log_string(f'Firstly check VoD capacity'))
	print(log_string(f'Buffer Level is {bufferLevel}'))
	print(log_string("Total episodes: " + str(episode_num)))

	time.sleep(3)

	for i in range(episode_num):
		print(log_string("Current episode: " + str(i + 1)))
		# if (i > 0) & (i % 3 == 1):
		# 	print(log_string(f'Frequently reboot starts'))
		# 	reboot_client()
		# 	time.sleep(20)
		# 	print(log_string(f'Frequently reboot is completed'))

		runEpisode(wait_time=wait_time, incomingTime=incomingTime, 
			outcomingTime=outcomingTime, clientNum=clientNum, bufferLevel=bufferLevel, Abr=Abr, withoutImg=withoutImg)
	print(log_string(f'All episodes are completed'))

def collectDataset(episode_num, remoteHostHandler, options:AutoDataGeneratorOptions, update=True):
	print(log_string(f'Firstly check VoD capacity'))
	print(log_string(f'Total number of Players is {options.NUM_OF_TOTAL_PLAYER}'))
	print(log_string(f'Num of Players in local host is {options.NUM_Of_PLAYER}'))
	print(log_string(f'Num of Players in remote host is {options.NUM_OF_TOTAL_PLAYER - options.NUM_Of_PLAYER}'))
	print(log_string(f'Buffer Time is {options.BUFFER_TIME}'))
	print(log_string(f'Total number of ClientIP is {len(IP_LIST) + len(REMOTE_IP_LIST)}'))
	print(log_string(f'run player number per a ClientIP is {options.MAX_PLAYER_PER_CLIENT} '))
	print(log_string("Total episodes: " + str(episode_num)))

	player_generator.setGeneratorOptions(options)

	time.sleep(3)

	update = update

	for i in range(episode_num):
		print(log_string("Current episode: " + str(i + 1)))
		# if (i > 0) & (i % 3 == 1):
		# 	print(log_string(f'Frequently reboot starts'))
		# 	reboot_client()
		# 	time.sleep(20)
		# 	print(log_string(f'Frequently reboot is completed'))

		runEpisode(remoteHostHandler, options, update)

		if i == 0:
			update = False
	print(log_string(f'All episodes are completed'))

def runEpisode(remoteHostHandler, options:AutoDataGeneratorOptions, update=True):
	print(log_string(f'Make script and players.'))
	shList, fnameList, htmlList = player_generator.generatePlayers(update=update)

	if update:
		remoteHostHandler.updateRemotePlayerFile()

	isRunning = [True]
	isTerminated = [False]
	run_thread = Thread(target=run_server, args=(isRunning, isTerminated,))
	run_thread.start()

	time.sleep(3)
	runPlayers_change(shList, htmlList, options, remoteHostHandler)
	time.sleep(7)

	close_server()

	while not isTerminated[0]:
		time.sleep(1)

	time.sleep(5)

def runPlayers_change(shList, htmlList, options:AutoDataGeneratorOptions, remoteHostHandler):
	wait_time = options.VIDEO_RUNNING_TIME
	incomingTime = options.INCOMMING_TIME
	outcomingTime = options.OUTCOMMING_TIME

	# set local client run target
	local_clientNum = len(IP_LIST)
	local_cListLen = local_clientNum

	if options.NUM_Of_PLAYER % options.MAX_PLAYER_PER_CLIENT == 0:
		local_cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT
	else:
		local_cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT + 1

	# set remote client run target
	remote_clientNum = len(REMOTE_IP_LIST)
	remote_cListLen = remote_clientNum

	if options.REMOTE_NUM_OF_PLAYER % options.MAX_PLAYER_PER_CLIENT == 0:
		remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.MAX_PLAYER_PER_CLIENT
	else:
		remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.MAX_PLAYER_PER_CLIENT + 1

	total_cListLen = local_cListLen + remote_cListLen

	out_client_list = [i for i in range(total_cListLen)]
	in_client_list = []
	start_time_slot = checkClientRuntime(poison_dist(comingTime=incomingTime, seed=random.randint(1,1000), clientNum=total_cListLen), incomingTime, total_cListLen)
	stop_time_slot = checkClientRuntime(poison_dist(comingTime=outcomingTime, seed=random.randint(1,1000), clientNum=total_cListLen), outcomingTime, total_cListLen)
	print(log_string('start time slot: ' + str(start_time_slot)))

	start_client_threads = []

	for i in range(incomingTime):
		s1 = time.time()
		if i in start_time_slot:
			for j in range(start_time_slot.count(i)):
				c = random.sample(out_client_list, 1)[0]
				in_client_list.append(c)
				out_client_list.remove(c)

				if c < local_clientNum:
					start_client_thread = Thread(target=startClient, args=(IP_LIST[c], shList,))
					print('\033[95m' + f'start client!: {IP_LIST[c]} at time {i}' + '\033[0m')
				else:
					start_client_thread = Thread(target=startRemoteClient, args=(REMOTE_IP_LIST[c-local_clientNum], remoteHostHandler,))
					print('\033[95m' + f'start client!: {REMOTE_IP_LIST[c-local_clientNum]} at time {i}' + '\033[0m')
				start_client_thread.start()
				start_client_threads.append(start_client_thread)
				# player_generator.runPlayers(IP_LIST[c], shList)
				
		s2 = time.time()

		if s2 - s1 < 1:
			time.sleep(1 - (s2-s1))

	time.sleep(wait_time)
	stop_client_threads = []
	
	print(log_string('stop time slot: ' + str(stop_time_slot)))
	for i in range(outcomingTime):
		s3 = time.time()
		if i in stop_time_slot:
			for j in range(stop_time_slot.count(i)):
				c = random.sample(in_client_list, 1)[0]
				out_client_list.append(c)
				in_client_list.remove(c)

				if c < local_clientNum:
					stop_client_thread = Thread(target=stopClient, args=(IP_LIST[c], options.MAX_PLAYER_PER_CLIENT, htmlList,))
					print('\033[95m'+f'stop client!: {IP_LIST[c]} at time {i + incomingTime + wait_time}'+'\033[0m')
				else:
					stop_client_thread = Thread(target=stopRemoteClient, args=(REMOTE_IP_LIST[c-local_clientNum], remoteHostHandler,))
					print('\033[95m'+f'stop client!: {REMOTE_IP_LIST[c-local_clientNum]} at time {i + incomingTime + wait_time}'+'\033[0m')
				stop_client_thread.start()
				stop_client_threads.append(stop_client_thread)		
				# reboot_client(CLIENT_NAME[c])
		# print(log_string(f'current i is {i}'))
		s4 = time.time()

		if s4 - s3 < 1:
			time.sleep(1 - (s4-s3))

	print(log_string('start client thread joining'))
	for sct in start_client_threads:
		sct.join()

	print(log_string('stop client thread joining'))
	for sct in stop_client_threads:
		sct.join()

# should change to including remote host
def runPlayers(shList, htmlList, options:AutoDataGeneratorOptions):
	wait_time = options.VIDEO_RUNNING_TIME
	incomingTime = options.INCOMMING_TIME
	outcomingTime = options.OUTCOMMING_TIME

	clientNum = len(IP_LIST)
	cListLen = clientNum

	if options.NUM_Of_PLAYER % options.MAX_PLAYER_PER_CLIENT == 0:
		cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT
	else:
		cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT + 1

	out_client_list = [i for i in range(cListLen)]
	# print(log_string(str(out_client_list)))
	in_client_list = []
	start_time_slot = checkClientRuntime(poison_dist(comingTime=incomingTime, seed=random.randint(1,1000), clientNum=cListLen), incomingTime, cListLen)
	stop_time_slot = checkClientRuntime(poison_dist(comingTime=outcomingTime, seed=random.randint(1,1000), clientNum=cListLen), outcomingTime, cListLen)
	print(log_string('start time slot: ' + str(start_time_slot)))

	start_client_threads = []

	for i in range(incomingTime):
		s1 = time.time()
		if i in start_time_slot:
			for j in range(start_time_slot.count(i)):
				c = random.sample(out_client_list, 1)[0]
				in_client_list.append(c)
				out_client_list.remove(c)
				start_client_thread = Thread(target=startClient, args=(IP_LIST[c], shList,))
				start_client_thread.start()
				start_client_threads.append(start_client_thread)
				# player_generator.runPlayers(IP_LIST[c], shList)
				print('\033[95m' + f'start client!: {IP_LIST[c]} at time {i}' + '\033[0m')

		s2 = time.time()

		if s2 - s1 < 1:
			time.sleep(1 - (s2-s1))

	time.sleep(wait_time)
	stop_client_threads = []
	
	print(log_string('stop time slot: ' + str(stop_time_slot)))
	for i in range(outcomingTime):
		s3 = time.time()
		if i in stop_time_slot:
			for j in range(stop_time_slot.count(i)):
				c = random.sample(in_client_list, 1)[0]
				out_client_list.append(c)
				in_client_list.remove(c)
				print('\033[95m'+f'stop client!: {IP_LIST[c]} at time {i + incomingTime + wait_time}'+'\033[0m')
				# stopClient(IP_LIST[c])
				stop_client_thread = Thread(target=stopClient, args=(IP_LIST[c], options.MAX_PLAYER_PER_CLIENT, htmlList,))
				stop_client_thread.start()
				stop_client_threads.append(stop_client_thread)		
				# reboot_client(CLIENT_NAME[c])
		# print(log_string(f'current i is {i}'))
		s4 = time.time()

		if s4 - s3 < 1:
			time.sleep(1 - (s4-s3))

	print(log_string('start client thread joining'))
	for sct in start_client_threads:
		sct.join()

	print(log_string('stop client thread joining'))
	for sct in stop_client_threads:
		sct.join()

def startRemoteClient(clientIP, remoteHostHandler):
	remoteHostHandler.runRemotePlayers(clientIP)

def startClient(clientIP, shList):
	player_generator.runPlayers(clientIP, shList)

def stopRemoteClient(clientIP, remoteHostHandler):
	remoteHostHandler.stopRemotePlayers(clientIP)

def stopClient(clientIP, MAX_PLAYER_PER_CLIENT, htmlList):
	head_ip_index = IP_LIST.index(clientIP)
	head_html_index = head_ip_index * MAX_PLAYER_PER_CLIENT

	player_generator.stopPlayers(head_html_index, htmlList)

def terminatePlayers(options, remoteHostHandler):
	player_generator.setGeneratorOptions(options)
	_, _, htmlList = player_generator.generatePlayers(update=False, keyboardInterrupt=True)

	# set local client run target
	local_clientNum = len(IP_LIST)
	local_cListLen = local_clientNum

	if options.NUM_Of_PLAYER % options.MAX_PLAYER_PER_CLIENT == 0:
		local_cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT
	else:
		local_cListLen = options.NUM_Of_PLAYER // options.MAX_PLAYER_PER_CLIENT + 1

	# set remote client run target
	remote_clientNum = len(REMOTE_IP_LIST)
	remote_cListLen = remote_clientNum

	if options.REMOTE_NUM_OF_PLAYER % options.MAX_PLAYER_PER_CLIENT == 0:
		remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.MAX_PLAYER_PER_CLIENT
	else:
		remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.MAX_PLAYER_PER_CLIENT + 1

	stop_client_threads = []
	for i in range(local_cListLen):
		stop_client_thread = Thread(target=stopClient, args=(IP_LIST[i], options.MAX_PLAYER_PER_CLIENT, htmlList,))
		stop_client_thread.start()
		stop_client_threads.append(stop_client_thread)

	# Remote host terminate
	for i in range(remote_cListLen):
		stop_client_thread = Thread(target=stopRemoteClient, args=(REMOTE_IP_LIST[i], remoteHostHandler,))
		stop_client_thread.start()
		stop_client_threads.append(stop_client_thread)

	for sct in stop_client_threads:
		sct.join()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='player update?')
	parser.add_argument('-u', '--update', dest='update', help='client update?', action="store_true")
	parser.add_argument('-t', '--terminate', dest='terminate', help='client terminate', action="store_true")
	args = parser.parse_args()

	if args.terminate:
		options = AutoDataGeneratorOptions()
		terminatePlayers(options)
		exit()

	update = False

	if args.update:
		update = True

	options = AutoDataGeneratorOptions()
	remoteHostHandler = remoteHostHandler.RemoteHostHandler()
	remoteHostHandler.setOptions(options)

	if remoteHostHandler.isUsed():
		remoteHostHandler.writeRemotePlayerScript()

	try:
		collectDataset(episode_num=1, remoteHostHandler=remoteHostHandler, 
			options=options, update=update)
		# For getting training dataset
		# main(episode_num=1, Abr=True, bufferLevel=10, withoutImg=False)
		# main(episode_num=1, Abr=True, bufferLevel=15, withoutImg=False)
		# main(episode_num=1, Abr=True, bufferLevel=30, withoutImg=False)
		# main(episode_num=1, Abr=True, bufferLevel=60, withoutImg=False)
		# main(episode_num=1, Abr=True, bufferLevel=90, withoutImg=False)

		# For getting standard dataset
		# main(episode_num=15, Abr=True, bufferLevel=10, withoutImg=False)
		# main(episode_num=15, Abr=True, bufferLevel=15, withoutImg=False)
		# main(episode_num=15, Abr=True, bufferLevel=30, withoutImg=False)
		# main(episode_num=15, Abr=True, bufferLevel=60, withoutImg=False)
		# main(episode_num=15, Abr=True, bufferLevel=90, withoutImg=False)

		# # For getting test dataset
		# main(episode_num=1, Abr=False, bufferLevel=10, withoutImg=False)
		# main(episode_num=1, Abr=False, bufferLevel=15, withoutImg=False)
		# main(episode_num=1, Abr=False, bufferLevel=30, withoutImg=False)
		# main(episode_num=1, Abr=False, bufferLevel=60, withoutImg=False)
		# main(episode_num=1, Abr=False, bufferLevel=90, withoutImg=False)

		# main(episode_num=1, Abr=False, bufferLevel=15, withoutImg=True)
	except KeyboardInterrupt:
		terminatePlayers(options, remoteHostHandler)

	