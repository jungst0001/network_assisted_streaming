import paramiko, sys, scp, os, time
import argparse
import subprocess
import player_generator
import clientConfig
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import fileUpload

###############################################
			# VM INFO & VM OPTION #
USER = clientConfig.client_user
PASSWORD = clientConfig.client_password
# print(player_generator.globals())
PLAYER_CATEGORY = player_generator.PLAYER_CATEGORY

VM_RUN_DIR = clientConfig.REMOTE_DIR
VM_DASH_DIR = clientConfig.REMOTE_HTML_DIR

MAX_PLAYER_PER_CLIENT = player_generator.MAX_PLAYER_PER_CLIENT
###############################################
			# VM IP LIST & HOST NAME #
IP_LIST = clientConfig.clientIPList
CLIENT_NAME = clientConfig.clientHostName

###############################################
_LOG = "clientDistributeHandler.py"
_DEBUG = True

command_ls = "ls"
command_grep_category = "ps -ax | grep "+ PLAYER_CATEGORY + " " # "firefox" "google-chrome-stable"
command_grep = "ps -ax | grep "
command_stopPlayer = "kill -2 "
# command_runPlayer = "sh runPlayer.sh &"

def log_string(str):
	log = '\033[95m' + str + '\033[0m'
	return log

def createSSHClient(ip):
	sshClient = paramiko.SSHClient()
	sshClient.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	sshClient.connect(ip, username=USER, password=PASSWORD)

	return sshClient

def stopClient(x_th_player, html_filename=None):
	clientIP = _mapPlayerToClient(x_th_player)

	ssh_manager = fileUpload.SSHManager()
	ssh_manager.create_ssh_client(clientIP, USER, PASSWORD)

	if html_filename is None:
		lines = ssh_manager.send_command(command_grep_category)
	else:
		lines = ssh_manager.send_command(command_grep + html_filename)
	pid = lines[0].split()[0]
	ssh_manager.send_command(command_stopPlayer + pid)

	print(f'stop {pid} in client {clientIP}')
	ssh_manager.close_ssh_client()

def runPlayer(x_th_player, sh_filename):
	clientIP = _mapPlayerToClient(x_th_player)

	ssh_manager = fileUpload.SSHManager()
	ssh_manager.create_ssh_client(clientIP, USER, PASSWORD)

	command_runPlayer = f'sh {sh_filename} &'

	ssh_manager.ssh_client.exec_command(command_runPlayer)
	ssh_manager.close_ssh_client()

	print(f'{_LOG} player {clientIP}, run: {sh_filename}')

def runPlayers(clientIP, shList):
	head_ip_index = IP_LIST.index(clientIP)
	head_sh_index = head_ip_index * MAX_PLAYER_PER_CLIENT

	if head_sh_index + MAX_PLAYER_PER_CLIENT < len(shList):
		sh_range = range(head_sh_index, head_sh_index + MAX_PLAYER_PER_CLIENT)
	else:
		sh_range = range(head_sh_index, len(shList))

	# print(f'{_LOG} | player {clientIP}, sh_range: {sh_range}')

	ssh_manager = fileUpload.SSHManager()
	ssh_manager.create_ssh_client(clientIP, USER, PASSWORD)

	for i in sh_range:
		ssh_manager.ssh_client.exec_command(f'sh {shList[i]} &')
		if _DEBUG:
			print(f'{_LOG} | sh run player: {clientIP}, {shList[i]}')
		time.sleep(2)

	ssh_manager.close_ssh_client()

	# print(f'{_LOG} | {len(sh_range)} players in {clientIP}')

def _mapPlayerToClient(x_th_player):
	ip_index = x_th_player // MAX_PLAYER_PER_CLIENT

	ip = IP_LIST[ip_index]

	return ip

def sendPlayerToClient(sh_filename, html_filename, x_th_player=0):
	clientIP = _mapPlayerToClient(x_th_player)

	fileUpload.updateClients(sh_filename, clientIP, clientConfig.LOCAL_RUN_DIR, VM_RUN_DIR)
	fileUpload.updateClients(html_filename, clientIP, clientConfig.LOCAL_DASH_DIR, VM_DASH_DIR)

if __name__ == "__main__":
	x_th_player = 0

	sh_filename = 'test_abr_30.sh'
	html_filename = 'test_abr_30.html'


	print(f'{_LOG} verify send function')
	sendPlayerToClient(sh_filename, html_filename)

	print(f'{_LOG} verify start player function')
	runPlayer(x_th_player, sh_filename)

	print(f'waiting...')
	time.sleep(5)

	print(f'{_LOG} verify stop player function')
	stopClient(x_th_player, html_filename)
