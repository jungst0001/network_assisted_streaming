import os
import psutil
import subprocess
import player_script_maker
import player_blueprint
import time

##############################################
			# MAIN DIR PATH #
RUN_DIR = "/home/wins/jin/video_emulation/client/Client.conf/"
PLAYER_DIR = RUN_DIR + "dashjs/emulator/"

##############################################
		# Player Generator Options #
NUM_Of_PLAYER = 10
VIDEO_RUNNING_TIME = 30 # unit is second
PLAYER_CATEGORY = "firefox" # or "chrome"

MSERVER_URL = "http://192.168.122.2:8088" # static URL
BUFFER_TIME = 30 # unit is second
IS_ABR = "true" # or "false"
QUALITY_QUERY_INTERVAL = 1500 # unit is milisecond
SEND_MONITORING_INTERVAL = 2500 # unit is milisecond
ABR_STRATEGY = "Dynamic" # or "BOLA" | "L2A" | "LoLP" | "Throughput"

###############################################

LOG_LEVEL = "DEBUG" # or "INFO"

def generatePlayers():
	print("Generating players and running...")
	print(f'player number: {NUM_Of_PLAYER}')

	if LOG_LEVEL == "DEBUG":
		print(f'Video Server URL: {MSERVER_URL}')
		print(f'Buffer size(time): {BUFFER_TIME}')
		print(f'ABR: {IS_ABR}')
		print(f'video quality query interval: {QUALITY_QUERY_INTERVAL}')
		print(f'sending interval of monitoring data: {SEND_MONITORING_INTERVAL}')
		print(f'ABR Strategy: {ABR_STRATEGY}')

	shList = []
	pList = []
	for i in range(NUM_Of_PLAYER): 
		filename = "Bf" + str(BUFFER_TIME) + "-Abr-" + str(i)
		makePlayer(filename)
		# while True:
		# 	sh = runPlayer(filename)
		# 	parent = psutil.Process(sh.pid)
		# 	for child in parent.children(recursive=True):
		# 		if child.name() == PLAYER_CATEGORY:
		# 			if child.pid in pList:
		# 				# p.terminate()
		# 				continue
		# 			else:
		# 				pList.append(child)
		# 				break
		sh = runPlayer(filename)
		isConnected = False
		parent = psutil.Process(sh.pid)
		for child in parent.children(recursive=True):
			if LOG_LEVEL == "DEBUG":
				print(f'child name is : {child.name()}')

			if child.name() == PLAYER_CATEGORY:
				pList.append(child)
				# try:
				# raddrs = [conn.raddr for conn in child.connections()]
				# if LOG_LEVEL == "DEBUG":
				# 	print(f'{child}')
				# 	print(f'{filename}\'s child: {child.pid} raddrs: {raddrs}')
				# for raddr in raddrs:
				# 	if raddr.ip in MSERVER_URL:
				# 		isConnected = True
				# 		# pList.append(child)
				# 		break
				# except psutil.AccessDenied:
				# 	continue
		
		# if isConnected is False:
		# 	killPlayer(sh)
		# 	i -= 1
		# 	continue

		shList.append(sh)

		# if i != 0 and i % 3 == 0:
		# 	time.sleep(0.2)

		if LOG_LEVEL == "DEBUG":
			print(f'pid of script(sh): {sh.pid}')
			if len(pList) == 0:
				print(f'pid of player is none')
			else:
				print(f'pid of player({PLAYER_CATEGORY}): {pList[-1].pid}')


	for child in pList:
		raddrs = [conn.raddr for conn in child.connections()]
		if LOG_LEVEL == "DEBUG":
			print(f'{child}')
			print(f'{filename}\'s child: {child.pid} raddrs: {raddrs}')
		# for raddr in raddrs:
		# 	if raddr.ip in MSERVER_URL:
		# 		isConnected = True
		# 		# pList.append(child)
		# 		break

	return shList, pList

def runPlayer(filename): 
	if LOG_LEVEL == "DEBUG":
		print(f'run player: {filename}.sh')
	p = subprocess.Popen(['sh', RUN_DIR + filename + '.sh'])
	time.sleep(0.1)

	return p

def killPlayer(sh):
	parent = psutil.Process(sh.pid)
	for child in parent.children(recursive=True):
		child.terminate()
	sh.terminate()

def killPlayers(shList):
	for sh in shList:
		if LOG_LEVEL == "DEBUG":
			print(f'player pid {sh.pid} is being terminated.')
		parent = psutil.Process(sh.pid)
		for child in parent.children(recursive=True):
			child.terminate()
		sh.terminate()

		shList.remove(sh)

def clearPlayers():
	if LOG_LEVEL == "DEBUG":
		runfile_list = os.listdir(RUN_DIR)
		runfile_list = [file for file in runfile_list if file.endswith(".sh")]
		player_list = os.listdir(PLAYER_DIR)
		player_list = [file for file in player_list if file.endswith(".html")]

		print(f'run file number: {len(runfile_list)}')
		print(f'player file number: {len(player_list)}')
		print(f'Above two file lists are being removed')

	# run_shell_script = RUN_DIR + "*.sh"
	# player_script = PLAYER_DIR + "*.html"
	for i in range(len(runfile_list)):
		subprocess.Popen(['rm', RUN_DIR + runfile_list[i]])
	for i in range(len(player_list)):
		subprocess.Popen(['rm', PLAYER_DIR + player_list[i]])

def makePlayer(filename="test", ip="10.0.0.1"):
	scriptOption = player_blueprint.ScriptOption()
	scriptOption.mserver_url = MSERVER_URL
	scriptOption.buffer_time = BUFFER_TIME
	scriptOption.isAbr = IS_ABR
	scriptOption.received_quality_interval = QUALITY_QUERY_INTERVAL 
	scriptOption.send_monitoring_interval = SEND_MONITORING_INTERVAL
	scriptOption.strategy = ABR_STRATEGY
	scriptOption.ip = ip

	player_script_maker.writePlayer(scriptOption, filename, PLAYER_CATEGORY)

def main(shList):
	shList, pList = generatePlayers()

	time.sleep(VIDEO_RUNNING_TIME)

	killPlayers(shList)
	# clearPlayers()


if __name__ == '__main__':
	shList = []

	try:
		main(shList)
	except KeyboardInterrupt:
		print(f'Keyboard Interruption occured.')
		killPlayers(shList)
	finally:
		if len(shList) != 0:
			for sh in shList:
				parent = psutil.Process(sh.pid)
				for child in parent.children(recursive=True):
					child.terminate()
				sh.terminate()

				shList.remove(sh)
		# clearPlayers()