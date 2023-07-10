import sys, os
import json, traceback
import numpy as np

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
		self.resolution_ratio = remoteHostClientConfig.resolution_ratio 
		self.resol_plan_ratio = remoteHostClientConfig.resol_plan_ratio
		self.resol_plan_ratio = np.array(self.resol_plan_ratio)

		for rhd in self.rhdList:
			rhd.assignedPlayerNum = len(rhd.clientIPList)
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

	def _getPlayerAttributeInfo(self, maxPlayerNum):
		# print(f'{self._LOG} | _getPlayerAttributeInfo()')
		player_attribute_info = []

		client_num_list = []

		if np.sum(self.resol_plan_ratio) != maxPlayerNum:
			print(f'resolutionxplan summation is not equal to number of clients')
			print(f'you must edit player ratio in remoteHostClientConfig.py')
			print(f'program is forlcy terminated')

			print(f'resolXplan sum: {np.sum(self.resol_plan_ratio)}, Max remote client: {maxPlayerNum}')

			exit()

		for i in range(self.resol_plan_ratio.shape[0]):
			for j in range(self.resol_plan_ratio.shape[1]):
				for num in range(self.resol_plan_ratio[i][j]):
					player_attribute_info.append((i + 1, remoteHostClientConfig.RESOLUTION[j]))

		# print(f'{self._LOG} | player attribute info: {player_attribute_info}')

		return player_attribute_info

	def _makePlayer(self, remoteHostData, filename="test", ip="10.0.0.1", attribute_info=(2, (854, 480))):
		scriptOption = player_blueprint.ScriptOption()
		scriptOption.mserver_url = remoteHostData.mserverURL
		scriptOption.cserver_url = remoteHostData.cserverURL
		scriptOption.buffer_time = self.options.BUFFER_TIME
		scriptOption.isAbr = self.options.IS_ABR
		scriptOption.received_quality_interval = self.options.QUALITY_QUERY_INTERVAL 
		scriptOption.strategy = self.options.ABR_STRATEGY
		scriptOption.ip = ip
		scriptOption.width = attribute_info[1][0]
		scriptOption.height = attribute_info[1][1]
		scriptOption.plan = attribute_info[0]

		# print(f'{self._LOG} | client {ip} attribute_info: {attribute_info}')

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
		maxPlayerPerNum = self.options.REMOTE_MAX_PLAYER_PER_CLIENT

		# print(f'remote buffer time: {self.options.BUFFER_TIME}')

		attribute_info = self._getPlayerAttributeInfo(remainPlayerNum)

		for rhd in self.rhdList:
			for i in range(currentPlayerNum, currentPlayerNum + rhd.assignedPlayerNum): 
				# print(f'remote buffer time: {self.options.BUFFER_TIME}')
				filename = "Bf" + str(self.options.BUFFER_TIME) + "-Abr-" + str(i)
				rhd.fnameList.append(filename)
				ip = player_generator.createVirtualIP(i)
				sh_filename, html_filename = self._makePlayer(rhd, filename, ip, attribute_info[i])

				rhd.htmlFileList.append(html_filename)
				rhd.shFileList.append(sh_filename)

			if rhd.assignedPlayerNum != 0:
				self._writeRemoteOptions(rhd, maxPlayerPerNum)
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
	rh = RemoteHostHandler()
	rh.setOptions(options)

	# print(rh._getScreenResolutionListForRatio())
	
	# rh.updateRemoteJSFile()
	rh.updateRemoteSHFile()
	rh.updateRemoteHTMLFile()

if __name__ == '__main__':
	main()