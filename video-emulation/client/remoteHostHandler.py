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

		self.rhdList = remoteHostClientConfig.setRemoteHostData()

		# num of total applied ratio is len(rhdList)
		self.player_ratio = remoteHostClientConfig.player_ratio  

		for rhd in self.rhdList:
			rhd.sshManager = fileUpload.SSHManager()
			print(f'{self._LOG} init rhd: {rhd}')
			rhd.sshManager.create_ssh_client(rhd.remoteHost_IP,
				rhd.remoteHost_User, rhd.remoteHost_Password, rhd.remoteHost_PORT)

	def __del__(self):
		for rhd in self.rhdList:
			rhd.sshManager.close_ssh_client()

	def setOptions(self, options:AutoDataGeneratorOptions):
		self.options = options

	def isUsed(self):
		if self.options is not None:
			if self.options.REMOTE_NUM_OF_PLAYER > 0:
				return True

		return False

	def getRunClientIPList(self):
		totalClientIPList = []

		for rhd in self.rhdList:
			clientIPList = rhd.clientIPList[:rhd.assignedPlayerNum]
			totalClientIPList.extend(clientIPList) 

		return totalClientIPList

	def _getPlayerNumforRatio(self):
		# print(f'{self._LOG} | _getPlayerNumforRatio()')
		pns = []

		if len(self.player_ratio) < len(self.rhdList):
			print(f'player ratio is smaller than remoteHostData')
			print(f'you must edit player ratio in remoteHostClientConfig.py')
			print(f'program is forlcy terminated')

			exit()

		for i in range(len(self.rhdList)):
			pn = self.options.REMOTE_NUM_OF_PLAYER * self.player_ratio[i] // sum(self.player_ratio)

			pns.append(pn)

		if self.options.REMOTE_NUM_OF_PLAYER != sum(pns):
			pns[0] = pns[0] + self.options.REMOTE_NUM_OF_PLAYER - sum(pns)

		print(f'remote player_ratio: {pns}')

		for i in range(len(self.rhdList)):
			self.rhdList[i].assignedPlayerNum = pns[i]

			if pns[i] % self.options.REMOTE_MAX_PLAYER_PER_CLIENT == 0:
				self.rhdList[i].runableClientNum = pns[i] // self.options.REMOTE_MAX_PLAYER_PER_CLIENT
			else:
				self.rhdList[i].runableClientNum = pns[i] // self.options.REMOTE_MAX_PLAYER_PER_CLIENT + 1

	def _makePlayer(self, remoteHostData, filename="test", ip="10.0.0.1"):
		scriptOption = player_blueprint.ScriptOption()
		scriptOption.mserver_url = remoteHostData.mserverURL
		scriptOption.cserver_url = remoteHostData.cserverURL
		scriptOption.buffer_time = self.options.BUFFER_TIME
		scriptOption.isAbr = self.options.IS_ABR
		scriptOption.received_quality_interval = self.options.QUALITY_QUERY_INTERVAL 
		scriptOption.send_monitoring_interval = self.options.SEND_MONITORING_INTERVAL
		scriptOption.snapshot_interval = self.options.SNAPSHOT_INTERVAL
		scriptOption.strategy = self.options.ABR_STRATEGY
		scriptOption.ip = ip

		sh_filename, html_filename = player_script_maker.writePlayer(scriptOption, filename)

		return sh_filename, html_filename

	def resetRemotePlayerFile(self):
		for rhd in self.rhdList:
			rhd.fnameList = []
			rhd.htmlFileList = []
			rhd.shFileList = []

	def updateRemotePlayerFile(self):
		for rhd in self.rhdList:
			for file in rhd.shFileList:
				# print(f'{self._LOG} | {rhd} update remote sh file')
				rhd.sshManager.send_file(rhd.LOCAL_RUN_DIR + file, rhd.REMOTE_DIR)
			if rhd.assignedPlayerNum != 0:
				self._updateRemoteSHFile(rhd)

			for file in rhd.htmlFileList:
				# print(f'{self._LOG} | {rhd} update remote html file')
				rhd.sshManager.send_file(rhd.LOCAL_DASH_DIR + file, rhd.REMOTE_HTML_DIR)

			if rhd.assignedPlayerNum != 0:
				self._updateRemoteHTMLFile(rhd)

	# This is a basic function to running AutoDataGenerator 
	def writeRemotePlayerScript(self):
		currentPlayerNum = self.options.NUM_Of_PLAYER
		remainPlayerNum = self.options.REMOTE_NUM_OF_PLAYER
		maxPlayerNum = self.options.REMOTE_MAX_PLAYER_PER_CLIENT

		print(f'remote buffer time: {self.options.BUFFER_TIME}')

		self._getPlayerNumforRatio() # assign player num with player ratio

		for rhd in self.rhdList:
			for i in range(currentPlayerNum, currentPlayerNum + rhd.assignedPlayerNum): 
				# print(f'remote buffer time: {self.options.BUFFER_TIME}')
				filename = "Bf" + str(self.options.BUFFER_TIME) + "-Abr-" + str(i)
				rhd.fnameList.append(filename)
				ip = player_generator.createVirtualIP(i)
				sh_filename, html_filename = self._makePlayer(rhd, filename, ip)

				rhd.htmlFileList.append(html_filename)
				rhd.shFileList.append(sh_filename)

			if rhd.assignedPlayerNum != 0:
				self._writeRemoteOptions(rhd, maxPlayerNum)
			currentPlayerNum = currentPlayerNum + rhd.assignedPlayerNum

	def _updateRemoteOptions(self, remoteHostData):
		print(f'{self._LOG} | {remoteHostData} update remote option file')

		local_option_dir_filename = remoteHostData.OPTION_DIR + remoteHostData.OPTION_FILENAME
		remote_option_dir = remoteHostData.OPTION_DIR
		remoteHostData.sshManager.send_file(local_option_dir_filename, remote_option_dir)

	def _writeRemoteOptions(self, remoteHostData, maxPlayerNum):
		# attribute:
		# num of remain players, num player per a client, shList, htmlList
		options = {}
		options['remainPlayerNum'] = remoteHostData.assignedPlayerNum
		options['maxPlayerNum'] = maxPlayerNum
		options['shFileList'] = remoteHostData.shFileList
		options['htmlFileList'] = remoteHostData.htmlFileList

		with open(remoteHostData.OPTION_DIR + remoteHostData.OPTION_FILENAME, 'w') as file:
			json.dump(options, file)

		self._updateRemoteOptions(remoteHostData)

	def _updateRemoteJSFile(self, remoteHostData):
		# command that js file send to clients
		# use clientDistributeHandler
		lines = remoteHostData.sshManager.send_command(remoteHostData.remote_command_py + ' -j')
		for line in lines:
			print(f'{self._LOG} | {remoteHostData}: {line}')

	def updateRemoteJSFile(self, remoteHostData):
		for file in remoteHostData.FILE_LIST:
			remoteHostData.sshManager.send_file(remoteHostData.LOCAL_JS_DIR + file, remoteHostData.REMOTE_JS_DIR)
		self._updateRemoteJSFile(remoteHostData)

	def _updateRemoteSHFile(self, remoteHostData):
		# command that js file send to clients
		# use clientDistributeHandler
		lines = remoteHostData.sshManager.send_command(remoteHostData.remote_command_py + ' -s')
		for line in lines:
			print(f'{self._LOG} | {remoteHostData}:{line}')

	def updateRemoteSHFile(self, remoteHostData):
		for file in remoteHostData.shFileList:
			remoteHostData.sshManager.send_file(remoteHostData.LOCAL_RUN_DIR + file, remoteHostData.REMOTE_DIR)
		self._updateRemoteSHFile(remoteHostData)

	def _updateRemoteHTMLFile(self, remoteHostData):
		# command that js file send to clients
		# use clientDistributeHandler
		lines = remoteHostData.sshManager.send_command(remoteHostData.remote_command_py + ' -d')
		# print(stdout)
		for line in lines:
			print(f'{self._LOG} | {remoteHostData}:{line}')

	def updateRemoteHTMLFile(self, remoteHostData):
		for file in remoteHostData.htmlFileList:
			remoteHostData.sshManager.send_file(remoteHostData.LOCAL_DASH_DIR + file, remoteHostData.REMOTE_HTML_DIR)
		self._updateRemoteHTMLFile(remoteHostData)

	def runRemotePlayers(self, clientIP):
		for rhd in self.rhdList:
			if clientIP in rhd.clientIPList:
				rhd.sshManager.send_command(rhd.remote_command_py + ' -r ' + clientIP)

	def stopRemotePlayers(self, clientIP):
		for rhd in self.rhdList:
			if clientIP in rhd.clientIPList:
				lines = rhd.sshManager.send_command(rhd.remote_command_py + ' -t ' + clientIP)
				for line in lines:
					print(f'{self._LOG} | {line}')

def main():
	options = AutoDataGeneratorOptions()
	rh = rh.RemoteHostHandler()
	rh.setOptions(options)
	
	rh.updateRemoteJSFile()
	rh.updateRemoteSHFile()
	rh.updateRemoteHTMLFile()

if __name__ == '__main__':
	main()