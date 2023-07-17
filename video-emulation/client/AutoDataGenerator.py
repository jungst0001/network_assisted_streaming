import subprocess
import argparse
import numpy as np
from math import factorial, exp
import time, sys
import random
import paramiko
import select
from threading import Thread
import requests, json
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
		self.REMOTE_NUM_OF_PLAYER = 25
		self.NUM_OF_TOTAL_PLAYER = self.NUM_Of_PLAYER + self.REMOTE_NUM_OF_PLAYER

		self.VIDEO_RUNNING_TIME = 200 # unit is second
		self.PLAYER_CATEGORY = "firefox" # or "firefox" "google-chrome-stable"

		self.MSERVER_URL = "http://143.248.57.162" # static URL
		self.CSERVER_URL = "http://143.248.57.162:8888" # static URL
		self.RSERVER_URL = "http://192.168.122.1:8889"
		self.BUFFER_TIME = 4 # unit is second
		self.IS_ABR = "true" # "true" or "false", false means use rl quality
		self.QUALITY_QUERY_INTERVAL = 2000 # unit is milisecond
		self.ABR_STRATEGY = "Throughput" # or "Dynamic" | "BOLA" | "L2A" | "LoLP" | "Throughput"
		self.WIDTH = None
		self.HEIGHT = None

		###############################################
				# VM OPTION #
		self.LOCAL_MAX_PLAYER_PER_CLIENT = 1
		self.REMOTE_MAX_PLAYER_PER_CLIENT = 1
		###############################################
				# Auto OPTION #
		self.INCOMMING_TIME = 50
		self.OUTCOMMING_TIME = 50

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
	tp = paramiko.Transport(("127.0.0.1", 22)) # CSERVER IP
	tp.connect(username='wins', password='wins2-champion')

	channel = tp.open_session()
	channel.get_pty()
	channel.set_combine_stderr(1)
	channel.exec_command("cd jin/video_emulation/control_server && python3 server_flask.py")

	while isRunning[0]:
		if channel.exit_status_ready():
			if channel.recv_ready():
				break
		output = channel.recv(1024).decode(sys.stdout.encoding)
		sys.stdout.write(output)

		if "maximum" in output:
			isRunning[0] = False

	print(log_string("Channel closing"))
	channel.close()

	isTerminated[0] = True

def close_server():
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	ssh.connect("127.0.0.1", username="wins", password="wins2-champion")

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

	stdin, stdout, stderr = ssh.exec_command("rm /home/wins/jin/video_emulation/control_server/cacheStorage/*")
	stdin, stdout, stderr = ssh.exec_command("rm /home/wins/jin/video_emulation/control_server/images/*.jpeg")
	stdin, stdout, stderr = ssh.exec_command("rm /home/wins/jin/video_emulation/control_server/images/server_images/*.jpeg")

	ssh.close()

	print(log_string("Server closed"))

def collectDataset(episode_num, remoteHostHandler, options:AutoDataGeneratorOptions, update=True):
	# print(log_string(f'Firstly check VoD capacity'))
	print(log_string(f'Total number of Players is {options.NUM_OF_TOTAL_PLAYER}'))
	print(log_string(f'Num of Players in local host is {options.NUM_Of_PLAYER}'))
	print(log_string(f'Num of Players in remote host is {options.NUM_OF_TOTAL_PLAYER - options.NUM_Of_PLAYER}'))
	print(log_string(f'Buffer Time is {options.BUFFER_TIME}'))
	print(log_string(f'Abr(true) or RL(false) is {options.IS_ABR}'))
	print(log_string(f'Total number of ClientIP is {len(IP_LIST) + len(REMOTE_IP_LIST)}'))
	print(log_string(f'run player number per a local ClientIP is {options.LOCAL_MAX_PLAYER_PER_CLIENT} '))
	print(log_string(f'run player number per a remote ClientIP is {options.REMOTE_MAX_PLAYER_PER_CLIENT} '))
	print(log_string("Total episodes: " + str(episode_num)))

	player_generator.setGeneratorOptions(options)

	time.sleep(3)

	update = update

	try:
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
	except Exception as e:
		print(log_string(f'Error occurs when {i}/{episode_num}, in {options.BUFFER_TIME}'))
		raise e

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
	runPlayers(shList, htmlList, options, remoteHostHandler)
	time.sleep(7)

	close_server()

	while not isTerminated[0]:
		time.sleep(1)

	time.sleep(5)

def runPlayers(shList, htmlList, options:AutoDataGeneratorOptions, remoteHostHandler):
	wait_time = options.VIDEO_RUNNING_TIME
	incomingTime = options.INCOMMING_TIME
	outcomingTime = options.OUTCOMMING_TIME

	# set local client run target
	local_clientNum = len(IP_LIST)
	local_cListLen = local_clientNum

	if options.NUM_Of_PLAYER % options.LOCAL_MAX_PLAYER_PER_CLIENT == 0:
		local_cListLen = options.NUM_Of_PLAYER // options.LOCAL_MAX_PLAYER_PER_CLIENT
	else:
		local_cListLen = options.NUM_Of_PLAYER // options.LOCAL_MAX_PLAYER_PER_CLIENT + 1

	# set remote client run target
	remoteIPList = remoteHostHandler.getRunClientIPList()
	remote_clientNum = len(remoteIPList)
	remote_cListLen = remote_clientNum

	# if options.REMOTE_NUM_OF_PLAYER % options.REMOTE_MAX_PLAYER_PER_CLIENT == 0:
	# 	remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.REMOTE_MAX_PLAYER_PER_CLIENT
	# else:
	# 	remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.REMOTE_MAX_PLAYER_PER_CLIENT + 1

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

				if c < local_cListLen:
					start_client_thread = Thread(target=startClient, args=(IP_LIST[c], shList,))
					print('\033[95m' + f'start client!: {IP_LIST[c]} at time {i}' + '\033[0m')
				else:
					start_client_thread = Thread(target=startRemoteClient, args=(remoteIPList[c-local_cListLen], remoteHostHandler,))
					print('\033[95m' + f'start client!: {remoteIPList[c-local_cListLen]} at time {i}' + '\033[0m')
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

				if c < local_cListLen:
					stop_client_thread = Thread(target=stopClient, args=(IP_LIST[c], options.LOCAL_MAX_PLAYER_PER_CLIENT, htmlList,))
					print('\033[95m'+f'stop client!: {IP_LIST[c]} at time {i + incomingTime + wait_time}'+'\033[0m')
				else:
					stop_client_thread = Thread(target=stopRemoteClient, args=(remoteIPList[c-local_cListLen], remoteHostHandler, True,))
					print('\033[95m'+f'stop client!: {remoteIPList[c-local_cListLen]} at time {i + incomingTime + wait_time}'+'\033[0m')
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

def stopRemoteClient(clientIP, remoteHostHandler, runningCall=False):
	remoteHostHandler.stopRemotePlayers(clientIP)

	if runningCall:
		index = int(clientIP.split('.')[-1])
		ip = player_generator.createVirtualIP(index - 21)

		url = 'http://192.168.0.104:8888/disconnect'
		data = {}
		data['client_ip'] = ip
		requests.post(url, data=json.dumps(data))

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

	if options.NUM_Of_PLAYER % options.LOCAL_MAX_PLAYER_PER_CLIENT == 0:
		local_cListLen = options.NUM_Of_PLAYER // options.LOCAL_MAX_PLAYER_PER_CLIENT
	else:
		local_cListLen = options.NUM_Of_PLAYER // options.LOCAL_MAX_PLAYER_PER_CLIENT + 1

	# set remote client run target
	remoteIPList = remoteHostHandler.getRunClientIPList()
	remote_clientNum = len(remoteIPList)
	remote_cListLen = remote_clientNum

	# if options.REMOTE_NUM_OF_PLAYER % options.REMOTE_MAX_PLAYER_PER_CLIENT == 0:
	# 	remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.REMOTE_MAX_PLAYER_PER_CLIENT
	# else:
	# 	remote_cListLen = options.REMOTE_NUM_OF_PLAYER // options.REMOTE_MAX_PLAYER_PER_CLIENT + 1

	stop_client_threads = []
	for i in range(local_cListLen):
		stop_client_thread = Thread(target=stopClient, args=(IP_LIST[i], options.LOCAL_MAX_PLAYER_PER_CLIENT, htmlList,))
		stop_client_thread.start()
		stop_client_threads.append(stop_client_thread)

	# Remote host terminate
	for i in range(remote_cListLen):
		stop_client_thread = Thread(target=stopRemoteClient, args=(remoteIPList[i], remoteHostHandler,))
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
		remoteHostHandler = remoteHostHandler.RemoteHostHandler()
		remoteHostHandler.setOptions(options)
		terminatePlayers(options, remoteHostHandler)
		exit()

	update = True

	if args.update:
		update = False

	options = AutoDataGeneratorOptions()
	remoteHostHandler = remoteHostHandler.RemoteHostHandler()
	remoteHostHandler.setOptions(options)

	# if remoteHostHandler.isUsed():
	# 	remoteHostHandler.writeRemotePlayerScript()

	try:
		# update = True
		options.BUFFER_TIME = 4
		if update:
			remoteHostHandler.setOptions(options)
			remoteHostHandler.writeRemotePlayerScript()
		collectDataset(episode_num=1, remoteHostHandler=remoteHostHandler, 
			options=options, update=update)
		remoteHostHandler.resetRemotePlayerFile()

	except KeyboardInterrupt:
		terminatePlayers(options, remoteHostHandler)

	