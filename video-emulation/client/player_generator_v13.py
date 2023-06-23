import os
import psutil
import subprocess
import player_script_maker
import player_blueprint
import player_captureNetwork
import time

##############################################
			# MAIN DIR PATH #
RUN_DIR = "/home/wins/jin/video_emulation/client/Client.conf/"
PLAYER_DIR = RUN_DIR + "dashjs/emulator/"

##############################################
		# Player Generator Options #
NUM_Of_PLAYER = 500
VIDEO_RUNNING_TIME = 100 # unit is second
PLAYER_CATEGORY = "firefox" # or "firefox" "google-chrome-stable"

MSERVER_URL = "http://192.168.122.2:8088" # static URL
CSERVER_URL = "http://192.168.122.3:8888" # static URL
BUFFER_TIME = 30 # unit is second
IS_ABR = "true" # or "false"
QUALITY_QUERY_INTERVAL = 1500 # unit is milisecond
SEND_MONITORING_INTERVAL = 2500 # unit is milisecond
ABR_STRATEGY = "Dynamic" # or "BOLA" | "L2A" | "LoLP" | "Throughput"

###############################################
_LOG = "playre_generator.py"
_PLIST = []
LOG_LEVEL = "DEBUG" # or "INFO"

def catchPlayers(fnameList):
	pid2fname = {}
	pList = []
	cmd_ps = ['ps', '-ax']
	cmd_capture = ['grep']

	for fname in fnameList:
		cmd = cmd_capture.copy()
		cmd.append(fname)
		p1 = subprocess.Popen(cmd_ps, stdout=subprocess.PIPE)
		p2 = subprocess.Popen(cmd, stdin=p1.stdout, stdout=subprocess.PIPE)
		pout = p2.stdout.readline().split()
		if len(pout) == 0:
			if LOG_LEVEL == "DEBUG":
				print(f'{_LOG} There is no player: {fname}')
			continue
		else:
			pid = int(pout[0].decode())
			pList.append(psutil.Process(pid))
			pid2fname[(pid)] = fname

	return pList, pid2fname

def generatePlayers():
	print(f"Generating players and running...")
	print(f'player number: {NUM_Of_PLAYER}')

	if LOG_LEVEL == "DEBUG":
		print(f'{_LOG} logs')
		print(f'Video Server URL: {MSERVER_URL}')
		print(f'Buffer size(time): {BUFFER_TIME}')
		print(f'ABR: {IS_ABR}')
		print(f'video quality query interval: {QUALITY_QUERY_INTERVAL}')
		print(f'sending interval of monitoring data: {SEND_MONITORING_INTERVAL}')
		print(f'ABR Strategy: {ABR_STRATEGY}')

	shList = []
	fnameList = []
	for i in range(NUM_Of_PLAYER): 
		filename = "Bf" + str(BUFFER_TIME) + "-Abr-" + str(i)
		fnameList.append(filename)
		ip = createVirtualIP(i)
		makePlayer(filename, ip)

		if i // 20 != 0 and i % 20 == 0:
			time.sleep(7)
		sh = runPlayer(filename)
		shList.append(sh)

		if LOG_LEVEL == "DEBUG":
			print(f'{_LOG} pid of script(sh): {sh.pid}')

	return shList, fnameList

def createVirtualIP(index):
	ip = "10.0."
	MAX_INDEX = 255
	third = index // MAX_INDEX
	fourth = index % MAX_INDEX

	return ip + str(third) + '.' + str(fourth + 1)

def runPlayer(filename): 
	if LOG_LEVEL == "DEBUG":
		print(f'{_LOG} run player: {filename}.sh')
	p = subprocess.Popen(['sh', RUN_DIR + filename + '.sh'])
	time.sleep(0.5)

	return p

# def killPlayer(p):
# 	p.terminate()

# def killPlayers(pList):
# 	for p in pList:
# 		p.terminate()

def killPlayers():
	fnameList = ['/usr/lib/firefox/firefox']
	pList, _ = catchPlayers(fnameList)

	for p in pList:
		if LOG_LEVEL == "DEBUG":
			print(f'{_LOG} pid of a player is {p.pid}')
		p.terminate()

def killScript(sh):
	parent = psutil.Process(sh.pid)
	for child in parent.children(recursive=True):
		child.terminate()
	sh.terminate()

def killScripts(shList):
	for sh in shList:
		if LOG_LEVEL == "DEBUG":
			print(f'{_LOG} player pid {sh.pid} is being terminated.')
		parent = psutil.Process(sh.pid)
		for child in parent.children(recursive=True):
			child.terminate()
		sh.terminate()

		shList.remove(sh)

def clearScriptsAndPlayers():
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

def main():
	global _PLIST
	# player_captureNetwork.startPlayersMonitoring()
	shList, fnameList = generatePlayers()

	# pList, pid2fname = catchPlayers(fnameList)
	# _PLIST = pList
	# player_captureNetwork.matchingPIDtoPlayer(pid2fname)

	time.sleep(VIDEO_RUNNING_TIME)

	print(f'killing players...')
	killPlayers()
	# player_captureNetwork.stopPlayersMonitoring()

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(f'{_LOG} Keyboard Interruption occured.')
		# killPlayers(_PLIST)