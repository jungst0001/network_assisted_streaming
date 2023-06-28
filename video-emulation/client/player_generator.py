import os, time
import psutil
import subprocess
if __name__ == "__main__" or __name__ == "player_generator":
	import player_blueprint
	import player_script_maker
else:
	from . import player_script_maker
	from . import player_blueprint
# from . import player_captureNetwork

##############################################
			# MAIN DIR PATH #
RUN_DIR = "/home/wins/jin/video_emulation/client/Client.conf/"
PLAYER_DIR = RUN_DIR + "dashjs/emulator/"

##############################################
		# Player Generator Options #
NUM_Of_PLAYER = 20
VIDEO_RUNNING_TIME = 30 # unit is second
PLAYER_CATEGORY = "firefox" # or "firefox" "google-chrome-stable"

MSERVER_URL = "http://192.168.122.2:8088" # static URL
CSERVER_URL = "http://192.168.122.3:8888" # static URL
BUFFER_TIME = 30 # unit is second
IS_ABR = "true" # or "false"
QUALITY_QUERY_INTERVAL = 1500 # unit is milisecond
SEND_MONITORING_INTERVAL = 2500 # unit is milisecond
SNAPSHOT_INTERVAL = 5000
ABR_STRATEGY = "Dynamic" # or "BOLA" | "L2A" | "LoLP" | "Throughput"

###############################################
		# VM OPTION #
MAX_PLAYER_PER_CLIENT = 5
###############################################

_LOG = "player_generator.py"
_PLIST = []
LOG_LEVEL = "DEBUG" # or "INFO"
LOG_LEVEL = "INFO"

def setGeneratorOptions(options):
	from AutoDataGenerator import AutoDataGeneratorOptions

	global NUM_Of_PLAYER
	global BUFFER_TIME
	global IS_ABR
	global ABR_STRATEGY
	global VIDEO_RUNNING_TIME
	global MAX_PLAYER_PER_CLIENT
	global QUALITY_QUERY_INTERVAL

	NUM_Of_PLAYER = options.NUM_Of_PLAYER
	BUFFER_TIME = options.BUFFER_TIME
	IS_ABR = options.IS_ABR
	ABR_STRATEGY = options.ABR_STRATEGY
	VIDEO_RUNNING_TIME = options.VIDEO_RUNNING_TIME
	MAX_PLAYER_PER_CLIENT = options.LOCAL_MAX_PLAYER_PER_CLIENT
	QUALITY_QUERY_INTERVAL = options.QUALITY_QUERY_INTERVAL

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

def generatePlayers(update=True, keyboardInterrupt=False):
	if keyboardInterrupt == False:
		print(f"Generating players and running...")
		print(f'local player number: {NUM_Of_PLAYER}')

		if LOG_LEVEL == "DEBUG":
			print(f'{_LOG} logs')
			print(f'Video Server URL: {MSERVER_URL}')
			print(f'Control Server URL: {CSERVER_URL}')
			print(f'Buffer size(time): {BUFFER_TIME}')
			print(f'ABR: {IS_ABR}')
			print(f'video quality query interval: {QUALITY_QUERY_INTERVAL}')
			print(f'sending interval of monitoring data: {SEND_MONITORING_INTERVAL}')
			print(f'sending interval of snapshot data: {SNAPSHOT_INTERVAL}')
			print(f'ABR Strategy: {ABR_STRATEGY}')

	shList = []
	fnameList = []
	htmlList = []
	for i in range(NUM_Of_PLAYER): 
		filename = "Bf" + str(BUFFER_TIME) + "-Abr-" + str(i)
		fnameList.append(filename)
		ip = createVirtualIP(i)
		sh_filename, html_filename = makePlayer(filename, ip)

		if update:
			import clientDistributeHandler
			clientDistributeHandler.sendPlayerToClient(sh_filename, html_filename, x_th_player=i)

		htmlList.append(html_filename)
		shList.append(sh_filename)

	return shList, fnameList, htmlList

def runAllPlayers(shList):
	import clientDistributeHandler

	for i in range(NUM_Of_PLAYER):
		clientDistributeHandler.runPlayer(x_th_player=i, sh_filename=shList[i])

		if LOG_LEVEL == "DEBUG":
			print(f'{_LOG} script(sh): {shList[i]}')

def runPlayers(clientIP, shList):
	import clientDistributeHandler

	clientDistributeHandler.runPlayers(clientIP=clientIP, shList=shList)

def createVirtualIP(index):
	ip = "10.0."
	MAX_INDEX = 255
	third = index // MAX_INDEX
	fourth = index % MAX_INDEX

	return ip + str(third) + '.' + str(fourth + 1)

def stopAllPlayers(htmlList):
	first_sh_index = NUM_Of_PLAYER // MAX_PLAYER_PER_CLIENT
	index_list = [i * MAX_PLAYER_PER_CLIENT for i in range(first_sh_index)]

	import clientDistributeHandler

	for i in index_list:
		clientDistributeHandler.stopClient(i, htmlList[i])

		# i += MAX_PLAYER_PER_CLIENT # stop fast

def stopPlayers(x_th_player, htmlList):
	import clientDistributeHandler

	clientDistributeHandler.stopClient(x_th_player, htmlList[x_th_player])

### previos code (handle by process id)   ###
# def runPlayer(filename): 
# 	if LOG_LEVEL == "DEBUG":
# 		print(f'{_LOG} run player: {filename}.sh')
# 	p = subprocess.Popen(['sh', RUN_DIR + filename + '.sh'])
# 	time.sleep(0.5)

# 	return p

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

###################################################

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
	scriptOption.cserver_url = CSERVER_URL
	scriptOption.buffer_time = BUFFER_TIME
	scriptOption.isAbr = IS_ABR
	scriptOption.received_quality_interval = QUALITY_QUERY_INTERVAL 
	scriptOption.send_monitoring_interval = SEND_MONITORING_INTERVAL
	scriptOption.snapshot_interval = SNAPSHOT_INTERVAL
	scriptOption.strategy = ABR_STRATEGY
	scriptOption.ip = ip

	sh_filename, html_filename = player_script_maker.writePlayer(scriptOption, filename, PLAYER_CATEGORY)

	return sh_filename, html_filename

# below main code is previos code for handling pid
# def main():
	# global _PLIST
	# # player_captureNetwork.startPlayersMonitoring()
	# # pList, pid2fname = catchPlayers(fnameList)
	# # _PLIST = pList
	# # player_captureNetwork.matchingPIDtoPlayer(pid2fname)

	# time.sleep(VIDEO_RUNNING_TIME)

	# print(f'stop players...')
	# killPlayers()
	# player_captureNetwork.stopPlayersMonitoring()
	# htmlList = []
	# for i in range(NUM_Of_PLAYER): 
	# 	filename = "Bf" + str(BUFFER_TIME) + "-Abr-" + str(i)
	# 	# fnameList.append(filename)
	# 	ip = createVirtualIP(i)
	# 	sh_filename, html_filename = makePlayer(filename, ip)
	# 	htmlList.append(html_filename)


def main():
	shList, fnameList, htmlList = generatePlayers(update=False)

	runAllPlayers(shList)

	stopAllPlayers(htmlList)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		print(f'{_LOG} Keyboard Interruption occured.')
		# killPlayers(_PLIST)