import sys, os
import json, traceback
if __name__ == "__main__" or __name__ == "remoteHostHandler":
	import remoteHostClientConfig
	import player_generator
	import player_blueprint
	import player_script_maker
	from AutoDataGenerator import AutoDataGeneratorOptions
else:
	from . import remoteHostClientConfig
	from . import player_generator
	from . import player_blueprint
	from . import player_script_maker
	from .AutoDataGenerator import AutoDataGeneratorOptions

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
import fileUpload

class RemoteHostHandler:
	def __init__(self):
		self._LOG = "[RemoteHostHandler]"

		self.shFileList = []
		self.fnameList = []
		self.htmlFileList = []

		self.options = None

		self._remoteIP = remoteHostClientConfig.remoteHost_IP
		self._remotePort = remoteHostClientConfig.remoteHost_PORT
		self._remoteUser = remoteHostClientConfig.remoteHost_User
		self._remotePassword = remoteHostClientConfig.remoteHost_Password

		self._localDir = remoteHostClientConfig.LOCAL_DIR
		self._localRunDir = remoteHostClientConfig.LOCAL_RUN_DIR
		self._localDashDir = remoteHostClientConfig.LOCAL_DASH_DIR
		self._localJSDir = remoteHostClientConfig.LOCAL_JS_DIR
		
		self._remoteDir = remoteHostClientConfig.REMOTE_DIR
		self._remoteHTMLDir = remoteHostClientConfig.REMOTE_HTML_DIR
		self._remoteJSDir = remoteHostClientConfig.REMOTE_JS_DIR

		self._fileList = remoteHostClientConfig.FILE_LIST

		self._remoteOptionDir = remoteHostClientConfig.OPTION_DIR
		self._remoteOptionFilename = remoteHostClientConfig.OPTION_FILENAME

		self._remoteCommand = remoteHostClientConfig.remote_command_py

		self._sshManager = fileUpload.SSHManager()
		self._createSSHClient()

	def __del__(self):
		self._closeSSHClient()

	def setOptions(self, options:AutoDataGeneratorOptions):
		self.options = options

	def isUsed(self):
		if self.options is not None:
			if self.options.REMOTE_NUM_OF_PLAYER > 0:
				return True

		return False

	def _createSSHClient(self):
		self._sshManager.create_ssh_client(self._remoteIP, self._remoteUser, self._remotePassword, self._remotePort)

	def _closeSSHClient(self):
		self._sshManager.close_ssh_client()

	def _makePlayer(self, filename="test", ip="10.0.0.1"):
		scriptOption = player_blueprint.ScriptOption()
		scriptOption.mserver_url = self.options.MSERVER_URL_FOR_REMOTE_HOST
		scriptOption.cserver_url = self.options.CSERVER_URL_FOR_REMOTE_HOST
		scriptOption.buffer_time = self.options.BUFFER_TIME
		scriptOption.isAbr = self.options.IS_ABR
		scriptOption.received_quality_interval = self.options.QUALITY_QUERY_INTERVAL 
		scriptOption.send_monitoring_interval = self.options.SEND_MONITORING_INTERVAL
		scriptOption.snapshot_interval = self.options.SNAPSHOT_INTERVAL
		scriptOption.strategy = self.options.ABR_STRATEGY
		scriptOption.ip = ip

		sh_filename, html_filename = player_script_maker.writePlayer(scriptOption, filename)

		return sh_filename, html_filename

	def updateRemotePlayerFile(self):
		print(f'{self._LOG} | update remote player file')

		for file in self.shFileList:
			self._sshManager.send_file(self._localRunDir + file, self._remoteDir)
		self._updateRemoteSHFile()

		for file in self.htmlFileList:
			self._sshManager.send_file(self._localDashDir + file, self._remoteHTMLDir)
		self._updateRemoteHTMLFile()

	# This is a basic function to running AutoDataGenerator 
	def writeRemotePlayerScript(self):
		currentPlayerNum = self.options.NUM_Of_PLAYER
		remainPlayerNum = self.options.REMOTE_NUM_OF_PLAYER
		maxPlayerNum = self.options.REMOTE_MAX_PLAYER_PER_CLIENT
		# remote_mserver = options.MSERVER_URL_FOR_REMOTE_HOST
		# remote_cserver = options.CSERVER_URL_FOR_REMOTE_HOST
		# remote_rserver = options.RSERVER_URL_FOR_REMOTE_HOST

		for i in range(currentPlayerNum, currentPlayerNum + remainPlayerNum): 
			filename = "Bf" + str(self.options.BUFFER_TIME) + "-Abr-" + str(i)
			self.fnameList.append(filename)
			ip = player_generator.createVirtualIP(i)
			sh_filename, html_filename = self._makePlayer(filename, ip)

			self.htmlFileList.append(html_filename)
			self.shFileList.append(sh_filename)

		self._writeRemoteOptions(remainPlayerNum, maxPlayerNum)

	def _updateRemoteOptions(self):
		print(f'{self._LOG} | update remote option file')
		local_option_dir_filename = self._remoteOptionDir + self._remoteOptionFilename
		remote_option_dir = self._remoteOptionDir

		# self._createSSHClient()
		self._sshManager.send_file(local_option_dir_filename, remote_option_dir)
		# self._closeSSHClient()

	def _writeRemoteOptions(self, remainPlayerNum, maxPlayerNum):
		# attribute:
		# num of remain players, num player per a client, shList, htmlList
		options = {}
		options['remainPlayerNum'] = remainPlayerNum
		options['maxPlayerNum'] = maxPlayerNum
		options['shFileList'] = self.shFileList
		options['htmlFileList'] = self.htmlFileList

		with open(self._remoteOptionDir + self._remoteOptionFilename, 'w') as file:
			json.dump(options, file)

		self._updateRemoteOptions()

	def _updateRemoteJSFile(self):
		# command that js file send to clients
		# use clientDistributeHandler
		stdout = self._sshManager.send_command(self._remoteCommand + ' -j')
		print(stdout)

	def updateRemoteJSFile(self):
		# self._createSSHClient()

		for file in self._fileList:
			self._sshManager.send_file(self._localJSDir + file, self._remoteJSDir)
		self._updateRemoteJSFile()

		# self._closeSSHClient()

	def _updateRemoteSHFile(self):
		# command that js file send to clients
		# use clientDistributeHandler
		stdout = self._sshManager.send_command(self._remoteCommand + ' -s')
		print(stdout)

	def updateRemoteSHFile(self, shFileList):
		# self._createSSHClient()

		for file in shFileList:
			self._sshManager.send_file(self._localRunDir + file, self._remoteDir)
		self._updateRemoteSHFile()

		# self._closeSSHClient()

	def _updateRemoteHTMLFile(self):
		# command that js file send to clients
		# use clientDistributeHandler
		lines = self._sshManager.send_command(self._remoteCommand + ' -d')
		# print(stdout)
		for line in lines:
			print(f'{self._LOG} | {line}')

	def updateRemoteHTMLFile(self, htmlFileList):
		# self._createSSHClient()

		for file in htmlFileList:
			self._sshManager.send_file(self._localDashDir + file, self._remoteHTMLDir)
		self._updateRemoteHTMLFile()

		# self._closeSSHClient()

	def runRemotePlayers(self, clientIP):
		# self._createSSHClient()
		self._sshManager.send_command(self._remoteCommand + ' -r ' + clientIP)
		# self._closeSSHClient()

	def stopRemotePlayers(self, clientIP):
		# self._createSSHClient()
		lines = self._sshManager.send_command(self._remoteCommand + ' -t ' + clientIP)
		for line in lines:
			print(f'{self._LOG} | {line}')
		# self._closeSSHClient()

def main():
	options = AutoDataGeneratorOptions()
	rh = rh.RemoteHostHandler()
	rh.setOptions(options)
	
	rh.updateRemoteJSFile()
	rh.updateRemoteSHFile()
	rh.updateRemoteHTMLFile()

if __name__ == '__main__':
	main()