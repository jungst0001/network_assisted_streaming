import paramiko
import sys, argparse, os, time
import json
from scp import SCPClient, SCPException 
import remote_clientConfig_t1 as remote_clientConfig
import remote_fileUpload_t1 as remote_fileUpload
import remote_clientDistributeHandler_t1 as remote_clientDistributeHandler
from remote_clientDistributeHandler_t1 import command_grep, command_stopPlayer
import traceback

_DEBUG = True

class RemoteClientHandler:
	def __init__(self):
		self._LOG = "[RemoteClientHandler]"

		self.shFileList = None
		self.htmlFileList = None
		self.remainPlayerNum = None
		self.maxPlayerNum = None

		self.clientIPList = remote_clientConfig.clientIPList

		self.user = remote_clientConfig.client_user
		self.password = remote_clientConfig.client_password

		self._resolveRemoteOption()

	def _resolveRemoteOption(self):
		option_dir = remote_clientConfig.OPTION_DIR
		option_filename = remote_clientConfig.OPTION_FILENAME

		with open(option_dir + option_filename, 'r') as file:
			data = json.load(file)
			self.remainPlayerNum = data['remainPlayerNum']
			self.maxPlayerNum = data['maxPlayerNum']
			self.shFileList = data['shFileList']
			self.htmlFileList = data['htmlFileList']

	def mapPlayerToClient(self, x_th_player):
		ip_index = x_th_player // self.maxPlayerNum

		ip = self.clientIPList[ip_index]

		return ip

	def runPlayers(self, clientIP):
		head_ip_index = self.clientIPList.index(clientIP)
		head_sh_index = head_ip_index * self.maxPlayerNum

		if head_sh_index + self.maxPlayerNum < len(self.shFileList):
			sh_range = range(head_sh_index, head_sh_index + self.maxPlayerNum)
		else:
			sh_range = range(head_sh_index, len(self.shFileList))

		# print(f'{self._LOG} | player {clientIP}, sh_range: {sh_range}')

		ssh_manager = remote_fileUpload.SSHManager()
		ssh_manager.create_ssh_client(clientIP, self.user, self.password)

		for i in sh_range:
			ssh_manager.ssh_client.exec_command(f'sh {self.shFileList[i]} &')
			if _DEBUG:
				print(f'{self._LOG} | sh run player: {clientIP}, {self.shFileList[i]}')
			time.sleep(2)

		ssh_manager.close_ssh_client()

	def stopPlayers(self, clientIP):
		head_ip_index = self.clientIPList.index(clientIP)
		head_html_index = head_ip_index * self.maxPlayerNum

		ssh_manager = remote_fileUpload.SSHManager()
		ssh_manager.create_ssh_client(clientIP, self.user, self.password)

		lines = ssh_manager.send_command(command_grep + self.htmlFileList[head_html_index])
		pid = lines[0].split()[0]
		ssh_manager.send_command(command_stopPlayer + pid)

		print(f'stop {self.htmlFileList[head_html_index]} with {pid} in client {clientIP}')
		ssh_manager.close_ssh_client()

def main():
	parser = argparse.ArgumentParser(description='clients')
	parser.add_argument('-s', '--sh-update', dest='sh_update', help='sh update', action="store_true")
	parser.add_argument('-d', '--html-update', dest='html_update', help='html update', action="store_true")
	parser.add_argument('-j', '--js-update', dest='js_update', help='client.js update', action="store_true")
	parser.add_argument('-r', '--run-client', dest='run_player', help='run players with a specific IP', default=None)
	parser.add_argument('-t', '--stop-client', dest='stop_player', help='stop players with a specific IP', default=None)
	args = parser.parse_args()

	try:
		handler = RemoteClientHandler()
	except:
		print(f'[remtoeClientHandler] Error occurs. forcly terminated')
		print(traceback.format_exc())
		exit()

	if args.js_update:
		remote_fileUpload.updateClients()
		pass

	if args.sh_update:
		for shfile in handler.shFileList:
			remote_fileUpload.updateClients(shfile,
				handler.mapPlayerToClient(handler.shFileList.index(shfile)),
				remote_clientConfig.LOCAL_RUN_DIR, 
				remote_clientConfig.REMOTE_DIR)


	if args.html_update:
		for htmlfile in handler.htmlFileList:
			remote_fileUpload.updateClients(htmlfile,
				handler.mapPlayerToClient(handler.htmlFileList.index(htmlfile)),
				remote_clientConfig.LOCAL_DASH_DIR, 
				remote_clientConfig.REMOTE_HTML_DIR)

	if args.run_player is not None:
		# TODO:
		# implement that run player function
		# refer the remote_clientDistributeHandler 
		handler.runPlayers(args.run_player)

	elif args.stop_player is not None:
		# TODO:
		# implement that stop player function
		# refer the remote_clientDistributeHandler
		handler.stopPlayers(args.stop_player)

if __name__ == '__main__':
	main()