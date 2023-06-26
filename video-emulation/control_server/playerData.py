import json
from datetime import datetime
from threading import Timer, Lock, Thread
import time
import base64
from cluster import ClusterAttribute, Cluster
from calculateSSIM import getClientSSIM
from calculateGMSD import getClientGMSD
# from multiprocessing import Process, Lock, Manager

_DEBUG = False

# will be deprecated
def getPlayer(players, ip: str, port: int):
	result, player = isPlayer(players, ip)

	if result is False:
		player = Player(ip, port)
		players.append(player)

		return player
	else:
		return player

# will be deprecated
def isPlayer(players, ip: str):
	for player in players:
		if player.ip == ip:
			return True, player

	return False, None

class PlayerTimer:
	def __init__(self, interval, function, ip=""):
		self._log = '[PlayerTimer]'
	
		self._playerIP = ip
		self.interval = interval
		self.function = function
		self.timer = Timer(self.interval, self.function)

	def run(self):
		self.timer.start()

	def cancel(self):
#		print(f'{self._log} PlayerTimer {self._playerIP} is cancelled')
		self.timer.cancel()

	def reset(self):
		self.timer.cancel()
		self.timer = Timer(self.interval, self.function)
		self.timer.start()
#		print(f'{self._log} the player {self._playerIP} timer is reset')

class Player:
	def __init__(self, ip: str, port=0, interval=100, attribute=ClusterAttribute.HIGH.name):
		self._log = '[Player]'
	
		# player IP, Port address
		self.ip = ip
		self.port = port
		self.threadList = []

		# player session live info
		self._initTime = datetime.now()
		self._initTimeStr = self._initTime.strftime('%y%m%d_%H:%M:%S')
		self._endTime = 0
		self._endTimeStr = None
		self._interval = interval
		self._isDisconnected = False

		# player video info
		self._video_resolution = []

		# player Metric info
		""" 
		first index: SSIM
		second index: bitrate (kbps)
		third index: buffer level (seconds)
		fourth index: framerate (fps)
		fifth index: time to be saved (seconds)
		
		stalling event

		startup delay (miliseconds)

		tx: network tx speed (KB)
		rx: network rx speed (KB)

		"""
		# self.playerResolution = None
		# self._startupDelay = 0
		# self.stallingEvent = 0
		# self.isStalling = False
		# self.checkInitDelay = True

		self._metricLock = Lock()
		self._imageLock = Lock()
		self._gmsdLock = Lock()

		self._locks = (self._metricLock, self._imageLock, self._gmsdLock)

		self._global._startupDelay = 0
		self._global.stallingEvent = 0
		self._global.isStalling = False
		self._global.checkInitDelay = True
		self._global._messageIndex = 0

		self._currentImageName = None
		self._currentFrameNumber = 0
		# self._gmsdList = []
		# self.metrics = []
		# self._imageList = []		

		self._variable = dict()
		self.playerResolution = dict()
		self.playerResolution["width"] = 0
		self.playerResolution["height"] = 0
		self._imageList = list()
		self._gmsdList = list()
		self.metrics = list()

		self._variable['startupDelay'] = 0
		self._variable['stallingEvent'] = 0
		self._variable['isStalling'] = False
		self._variable['checkInitDelay'] = True
		self._variable['messageIndex'] = 0

		# self._global._imageList = self._imageList
		# self._global._gmsdList = self._gmsdList
		# self._global._metrics = self.metrics

		self._attribute = attribute
		self._qualityIndex = 0

		self._SSIMBuffer = 0
		self._GMSDBuffer = 0
		self._networkStateBuffer = None

		self._timer = PlayerTimer(self._interval, self._setTimer, self.ip)
		self._timer.run()

		# self._processTimer = Timer(2, self._processJoin).start()

	def _setTimer(self):
		self._endTime = datetime.now()
		self._endTimeStr = self._endTime.strftime('%y%m%d_%H:%M:%S')
		self._isDisconnected = True

	def _threadJoin(self):
		for saveThread in self.threadList:
			saveThread.join()
			self.threadList.remove(saveThread)

	def disconnectPlayer(self):
		self._setTimer()
		# self._processTimer.cancel()

	def getStallingEvent(self):
		return self._variable['stallingEvent']

	def getStartupDelay(self):
		return self._variable['startupDelay']

	def setQualityIndex(self, qualityIndex):
		self._qualityIndex = qualityIndex

	def getQualityIndex(self):
		return self._qualityIndex

	def getAttribute(self):
		return self._attribute
	
	def setAttribute(self, attribute: Cluster):
		self._attribute = attribute

	def setPlayerEndTime(self, endTime):
		self._endTime = endTime

	def getPlayerEndTime(self):
		return self._endTime

	def getPlayerInitTime(self):
		return self._initTime

	def getPlayerLiveTime(self):
		liveTime = self._endTime - self._initTime
		return liveTime

	def getTimer(self):
		return self._timer

	def isDisconnected(self):
		return self._isDisconnected

	def getMetrics(self):
		return self.metrics

	def getCurrentMetric(self):
		if len(self.metrics) != 0:
			return self.metrics[-1]

		return None

	def getVariable(self):
		return self._variable

	def getPlayerResolution(self):
		if self.playerResolution is None:
			self.playerResolution = {}
			self.playerResolution["width"] = 0
			self.playerResolution["height"] = 0

		return self.playerResolution

	def _saveStartupDelay(self, data, _global):
		# save startupDelay
		try:
			self._variable['startupDelay'] = data['startupDelay']
			print(f'{self._log} | {self.ip} startup delay: {self._variable["startupDelay"]}')

			return True
		except KeyError:
			return False

	def _saveBufferStalled(self, data, _global):
		# save Buffer stalled event
		try:
			isStalled = data['BufferStalled']
			print(f'{self._log} | {self.ip} -  buffer stalling occur')

			self._variable['stallingEvent'] += 1

			return True
		except KeyError:
			return False

	def _saveImageData(self, data, _imageLock, _gmsdLock):
		# save Image data and calculate SSIM / GMSD
		if _DEBUG:
			print(f'{self._log} the player {self.ip} _saveImageData()')

		try:
			imageData = data['Snapshot']
			bitrate = data['bitrate']

			# print(type(str(imageData)))
			# print(f'{self._log} {self.ip} image: {str(imageData)[0:20]}')

			frameNumber = imageData["FrameNumber"]
			extension = imageData["Type"]
			image = imageData["Image"]

			_imageLock.acquire()
			try:
				# self._currentFrameNumber = frameNumber
				# self._currentImageName = self.ip + "-" + str(frameNumber) + '.' + extension

				_currentFrameNumber = frameNumber
				_currentImageName = self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension

				imageInfo = (_currentImageName, _currentFrameNumber)
				# self._imageList.append(imageInfo)
				self._imageList.append(imageInfo)
				
				f = open('images/' + self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension, 'wb')
				f.write(base64.b64decode(image))
				f.close()
			finally:
				_imageLock.release()
				pass

			if len(self._imageList) != 0:
				_gmsdLock.acquire()
				try:
					head_imageInfo = self._imageList[0]
					self._imageList.remove(head_imageInfo)
					currentGMSD = getClientGMSD(head_imageInfo[0], head_imageInfo[1])
					if _DEBUG:
						print(f'{self._log} the player {self.ip} gmsd is calculated: {currentGMSD}')

					self._gmsdList.append(currentGMSD)
				except:
					if _DEBUG:
						print(f'{self._log} the player {self.ip} gmsd is not calculated')
					pass
				finally:
					_gmsdLock.release()
					pass
			return True
		except KeyError:
			return False
		
	def _receivePlayerClose(self, data):
		# if player is closed, this message is received
		try:
			status = data["status"]
			print(f'{self._log} {self.ip} - player status: {status}')

			self._timer.cancel()
			self._setTimer()

			return True
		except KeyError:
			return False

	def _savePlayerResolution(self, data):
		# save player resolution
		try:
			player_resolution = data["resolution"]

			# self.playerResolution = {}
			self.playerResolution["width"] = player_resolution["width"]
			self.playerResolution["height"] = player_resolution["height"]

			print(f'{self._log} | {self.ip} player resolution: {self.playerResolution["width"]}x{self.playerResolution["height"]}')

			return True
		except KeyError:
			return False
	
	def _handleHeartBeat(self, data):
		# handle player heart beat
		try:
			heartbeat = data["heartbeat"]
			return True
		except KeyError:
			return False

	def _saveNetworkState(self, data):
		# handle only network state
		try:
			tx = data["tx"]
			rx = data["rx"]

			self._networkStateBuffer = {}
			self._networkStateBuffer['tx'] = tx
			self._networkStateBuffer['rx'] = rx

			# if self.ip == "192.168.0.15":
			# 	print(f'{self._log} {self.ip} received network state: tx:{tx}KBps, rx:{rx}KBps')

			return True
		except KeyError:
			return False

	def _checkPostMessageIndex(self, data):
		# handle only message index
		message_index = data['index']

		# print(f'{self._log} | {self.ip} receive index: {message_index}, current: {self._variable["messageIndex"]}')

		self._variable['messageIndex'] += 1

		# if self._messageIndex == message_index:
		# 	self._messageIndex += 1
		# else:
		# 	print(f'{self._log} | {self.ip} has different index: {message_index}, current: {self._messageIndex}')

	def saveSSIM(self, SSIM):
		self._SSIMBuffer = SSIM

	def saveGMSD(self, GMSD):
		self._GMSDBuffer = GMSD

	def savePlayerData(self, playerdata, serverInitTime):
		data = json.loads(playerdata)

		saveThread = Thread(target=self._savePlayerData, args=(data, serverInitTime, self._global, self._locks), daemon=True)

		self.threadList.append(saveThread)
		saveThread.start()

		saveThread.join()

	def _savePlayerData(self, data, serverInitTime, _global, _locks):
		_metricLock = _locks[0]
		_imageLock = _locks[1]
		_gmsdLock = _locks[2]

		# handle only player heartbeat
		# if self._handleHeartBeat(data):
		# 	return

		# handle only player closing
		if self._receivePlayerClose(data):
			return

		# handle only player resolution
		if self._savePlayerResolution(data):
			return

		# handle only startup delay
		if self._saveStartupDelay(data, _global):
			return

		# handle only buffer stalled event
		if self._saveBufferStalled(data, _global):
			return

		# handle only network state
		if self._saveNetworkState(data):
			return

		# handle only image data
		if self._saveImageData(data, _imageLock, _gmsdLock):
			return

		self._checkPostMessageIndex(data)

		metric = {}
		
		# save current player live time
		metric['time'] = (datetime.now() - serverInitTime).total_seconds()
		metric['time'] = round(metric['time'], 3)

		metric['bitrate'] = data['bitrate']

		# save SSIM
		# metric['SSIM'] = 0
		# if self._currentImageName is not None:
		# 	currentSSIM = getClientSSIM(self._currentImageName, self._currentFrameNumber)
		# 	self._currentImageName = None
		# 	metric['SSIM'] = currentSSIM
		# elif self._SSIMBuffer != 0:
		# 	metric['SSIM'] = self._SSIMBuffer
		# 	self._SSIMBuffer = 0

		metric['GMSD'] = 0

		if len(self._gmsdList) != 0:
			if _gmsdLock.acquire(block=False):
				try:
					if len(self._gmsdList) != 0:
						currentGMSD = self._gmsdList[0]
						self._gmsdList.remove(currentGMSD)

						metric['GMSD'] = currentGMSD
				finally:
					_gmsdLock.release()
					pass

		# if self._currentImageName is not None:
		# 	currentGMSD = getClientGMSD(self._currentImageName, self._currentFrameNumber)
		# 	self._currentImageName = None
		# 	metric['GMSD'] = currentGMSD
		# elif self._GMSDBuffer != 0:
		# 	metric['GMSD'] = self._GMSDBuffer
		# 	self._GMSDBuffer = 0

		# 	print(f'{self._log} {self.ip} current SSIM: {currentSSIM}')

		# if float(metric['bitrate']) == 1501:
		# 	metric['QoE'] = 1.0000
		# elif float(metric['bitrate']) == 800:
		# 	metric['QoE'] = 0.97547
		# elif float(metric['bitrate']) == 400:
		# 	metric['QoE'] = 0.94629
		# elif float(metric['bitrate']) == 200:
		# 	metric['QoE'] = 0.83532

		# save client network statistics
		# if self.ip == "192.168.0.15":
		# 	print(f'{self._log} {self.ip} time:{(datetime.now() - serverInitTime).total_seconds()}')
		# 	print(f'{self._log} {self.ip} save network state:{self._networkStateBuffer}')
		# 	print(f'{self._log} {self.ip} save SSIM:{metric["SSIM"]}')

		# if self._networkStateBuffer == None:
		# 	metric['tx'] = 0
		# 	metric['rx'] = 0
		# else:
		# 	metric['tx'] = self._networkStateBuffer['tx']
		# 	metric['rx'] = self._networkStateBuffer['rx']
		# 	self._networkStateBuffer = None

		# save framerate
		framerate = data['framerate'].split('/')
		if len(framerate) == 1:
			metric['framerate'] = data['framerate']
		else:
			metric['framerate'] = float(framerate[0]) / float(framerate[1])
			
		# save current buffer level
		metric['bufferLevel'] = data['bufferLevel']

		# save current throughput
		metric['throughput'] = data['throughput']

		if len(self.metrics) == 0:
			print(f'{self._log} | {self.ip} - initial bitrate: {metric["bitrate"]}')
			metric['bitrateSwitch'] = 0
			metric['stalling'] = 0
			metric['stallingTime'] = 0
			metric['initDelayTime'] = 0

			# if self._networkStateBuffer == None:
			# 	metric['tx'] = 0
			# 	metric['rx'] = 0
			# else:
			# 	metric['tx'] = self._networkStateBuffer['tx']
			# 	metric['rx'] = self._networkStateBuffer['rx']
			# 	self._networkStateBuffer = None

			# if float(metric['bufferLevel']) == 0:
			# 	print(f'{self._log} {self.ip} - Initial Delay occur')
			# 	metric['initDelayTime'] = 1
			# 	metric['stalling'] = 1
			# 	metric['stallingTime'] = 1
			# 	self.isStalling = True
			# else:
			# 	self.checkInitDelay = False
		else:
			metric['initDelayTime'] = self.metrics[-1]['initDelayTime']

			if self._variable['checkInitDelay'] == True and float(metric['bufferLevel']) == 0:
				metric['initDelayTime'] = self.metrics[-1]['initDelayTime'] + 1
			else:
				self._variable['checkInitDelay'] = False

			if float(metric['bufferLevel']) <= 1:
				if self._variable['isStalling'] == False:
					print(f'{self._log} | {self.ip} - stalling event occurs')
					# metric['stalling'] = self.metrics[-1]['stalling'] + 1
					metric['stalling'] = 1
					self._variable['isStalling'] = True
				else:
					# metric['stalling'] = self.metrics[-1]['stalling']
					metric['stalling'] = 1
				metric['stallingTime'] = self.metrics[-1]['stallingTime'] + 1
			else:
				# metric['stalling'] = self.metrics[-1]['stalling']
				metric['stalling'] = 0
				metric['stallingTime'] = self.metrics[-1]['stallingTime']
				self._variable['isStalling'] = False

			if int(self.metrics[-1]['bitrate']) == int(metric['bitrate']):
				# metric['bitrateSwitch'] = self.metrics[-1]['bitrateSwitch']
				metric['bitrateSwitch'] = 0
			else:
				# metric['bitrateSwitch'] = self.metrics[-1]['bitrateSwitch'] + 1
				metric['bitrateSwitch'] = 1
				print(f'{self._log} | {self.ip} changed bitrate: {metric["bitrate"]}')

			# if self._networkStateBuffer == None:
			# 	metric['tx'] = 0
			# 	metric['rx'] = 0
			# else:
			# 	metric['tx'] = self._networkStateBuffer['tx']
			# 	metric['rx'] = self._networkStateBuffer['rx']
			# 	self._networkStateBuffer = None

		# if self.ip == "10.0.0.5":
		# 	print(f'{self._log} | the player {self.ip} point 5 pass')

		_metricLock.acquire()
		try:
			self.metrics.append(metric)
			if _DEBUG:
				print(f'{self._log} the player {self.ip} metric is saved: {metric}')
		except:
			print(f'{self._log} the player {self.ip} metric is not saved: {self._variable["messageIndex"]}')
		finally:
			_metricLock.release()
			pass

if __name__ == "__main__":
	print('playerData.py main')	

	ip = "127.0.0.1"

	player = Player(ip)

	print(player.isDisconnected())
	time.sleep(3)
	player.getTimer().reset()
	time.sleep(2)
	print(player.isDisconnected())
	time.sleep(4)
	print(player.isDisconnected())

	print(player.getPlayerLiveTime())
