import json
from datetime import datetime
from threading import Timer, Lock, Thread
import time
import math
import base64
from cluster import ClusterAttribute, Cluster
from calculateSSIM import getClientSSIM
from calculateGMSD import getClientGMSD
from CacheHandler import CacheHandler

_DEBUG = False

class RequestThreadManager:
	def __init__(self):
		self.requestThreadList = []
		self.metricLock = Lock()
		self.imageLock = Lock()
		self.pqLock = Lock() # perceptual quality

	def joinThread(self):
		for rThread in self.requestThreadList:
			if rThread.is_alive():
				rThread.join()
				self.requestThreadList.remove(rThread)
			else:
				self.requestThreadList.remove(rThread)

class ClientData:
	def __init__(self, ip: str, port=0):
		self._log = '[ClientData]'

		self.rtm = RequestThreadManager()
		self.ch = CacheHandler()
	
		# player IP, Port address
		self.ip = ip
		self.port = port
		self.requestThreadList = []

		# player session live info
		self._initTime = datetime.now()
		self._initTimeStr = self._initTime.strftime('%y%m%d_%H:%M:%S')
		self._endTime = 0
		self._endTimeStr = None
		self._interval = interval
		self._isDisconnected = False

		# client screen info
		self.screen_resolution = None

		# client streaming info
		self._attribute = None

		self._qualityIndex = 0
		self._currentQuality = 0
		self.requestURLList = []
		
		self.initList = []
		self.currentInit = None
		self.chunkList = []
		self.currentChunk = None

		self.chunkInCache = {}

		# metrics
		self.metrics = []
		self.imageList = []
		self.pqList = []

	def getScreenResolution(self):
		if self.screen_resolution is None:
			self.screen_resolution = {}
			self.screen_resolution["width"] = 0
			self.screen_resolution["height"] = 0

		return self.screen_resolution

	def _getInitWithChunkURL(self, playhead, currentQuality, chunkUnit=2):
		chunkNumber = math.ceil(playhead / chunkUnit)
		chunkKey = f'2s{chunkNumber}.m4s'

		initURL = None
		for init in self.initList:
			if init['quality'] == currentQuality:
				initURL = init['url']

		chunkURL = None
		for chunk in self.chunkList:
			if chunk['url'] in chunkKey:
				if chunk['quality'] == currentQuality:
					chunkURL = chunk['url']

		return initURL, chunkURL

	def _getServerImageFromCache(self, frameNumber, playhead, currentQuality):
		initURL, chunkURL = self._getInitWithChunkURL(playhead, currentQuality)

		if (initURL is None) or (chunk is None):
			print(f'{self._log} {self.ip} init url or chunk url is None')

		chunkMP4 = self.ch.getChunkMP4(initURL, chunkURL)
		if chunkMP4 is None:
			print(f'{self._log} {self.ip} chunk mp4 with {initURL}, {chunkURL} is None')

		self.chunkInCache[frameNumber] = chunkMP4

	def _saveImageData(self, data):
		# save Image data and calculate SSIM / GMSD
		if _DEBUG:
			print(f'{self._log} the client {self.ip} _saveImageData()')

		try:
			imageData = data['captured']
			bitrate = data['bitrate']
			playhead = data['playhead']

			# print(type(str(imageData)))
			# print(f'{self._log} {self.ip} image: {str(imageData)[0:20]}')

			frameNumber = imageData["frameNumber"] -> chunk를 얻고
			extension = imageData["type"]
			image = imageData["image"]

			cacheThread = Thread(target=self._getServerImageFromCache, args=(frameNumber, playhead, self._currentQuality),)
			cacheThread.start()

			self.rtm.imageLock.acquire()
			try:
				_currentFrameNumber = frameNumber
				_currentImageName = self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension

				imageInfo = (_currentImageName, _currentFrameNumber)
				# self._imageList.append(imageInfo)
				self._imageList.append(imageInfo)
				
				f = open('images/' + self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension, 'wb')
				f.write(base64.b64decode(image))
				f.close()
			finally:
				self.rtm.imageLock.release()
				pass

			if len(self._imageList) != 0:
				self.rtm.pqLock.acquire()
				try:
					head_imageInfo = self._imageList[0]
					self.imageList.remove(head_imageInfo)
					
					cacheThread.join()
					chunkMP4 = self.chunkInCache[frameNumber]
					currentGMSD = getClientGMSD(head_imageInfo[0], head_imageInfo[1], chunkMP4, self._currentQuality)
					if _DEBUG:
						print(f'{self._log} the player {self.ip} gmsd is calculated: {currentGMSD}')

					self.pqList.append(currentGMSD)
				except:
					if _DEBUG:
						print(f'{self._log} the player {self.ip} gmsd is not calculated')
					pass
				finally:
					self.rtm.pqLock.release()
					pass
			return True
		except KeyError:
			return False

	def setQualityIndex(self, qualityIndex):
		self._qualityIndex = qualityIndex

	def getQualityIndex(self):
		return self._currentQuality

	def setAttribute(self, attribute):
		self._attribute = attribute

	def getAttribute(self):
		return self._attribute

	def isDisconnected(self):
		return self._isDisconnected

	def _receivePlayerClose(self, data):
		# if player is closed, this message is received
		try:
			status = data["status"]
			print(f'{self._log} {self.ip} - player status: {status}')

			self._isDisconnected = True

			return True
		except KeyError:
			return False

	def getCurrentMetric(self):
		if len(self.metrics) != 0:
			return self.metrics[-1]

		return None

	def _saveScreenResolution(self, data):
		# save Screen resolution
		try:
			screen_resolution = data["resolution"]

			self.screen_resolution["width"] = screen_resolution["width"]
			self.screen_resolution["height"] = screen_resolution["height"]

			print(f'{self._log} | {self.ip} screen resolution: {self.screen_resolution["width"]}x{self.screen_resolution["height"]}')

			return True
		except KeyError:
			return False

	def _isStalling(self, data):
		isStalling = data['isStalling']

		if isStalling == "True":
			print(f'{self._log} | {self.ip} stalling event occurs')
			return 1
		else:
			return 0

	def saveClientData(self, clientData, serverInitTime):
		data = json.loads(clientData)

		requestThread = Thread(target=self._saveClientData, args=(data, serverInitTime),)

		self.rtm.requestThreadList.append(requestThread)
		requestThread.start()

		requestThread.join()
		self.requestThreadList.remove(rThread)

	def _getPQvalue(self):
		pqValue = 0
		if len(self.pqList) != 0:
			if self.rtm.pqLock.acquire(block=False):
				try:
					if len(self.pqList) != 0:
						currentGMSD = self.pqList[0]
						self.pqList.remove(currentGMSD)

						pqValue = currentGMSD
				finally:
					self.rtm.pqLock.release()
					pass

		return pqValue

	def _getThroughput(self, data):
		request_length = data['request_length']
		response_length = data['response_length']
		requestInterval = data['requestInterval']

		total_length = (request_length + response_length) / 1000 # make Byte to KB

		return  total_length / requestInterval

	def _checkRequestURL(self, data):
		self.requestURLList.append(data['request_url'])
		initCacheThread = Thread(target=self.ch.initCacheData, args=(data['request_url']),)
		initCacheThread.start()

		if url.split('.')[-1] in 'mp4':
			currentInit = {}
			currentInit['url'] = data['request_url']
			currentInit['quality'] = data['request_url_quality']
			self.currentInit = currentInit
			self.initList.append(currentInit)

		elif url.split('.')[-1] in 'm4s':
			currentChunk = {}
			currentChunk['url'] = data['request_url']
			currentChunk['quality'] = data['request_url_quality']
			self.currentChunk = currentChunk
			self.chunkList.append(currentChunk)

		return initCacheThread

	def _saveClientData(self, data, serverInitTime):
		self._currentQuality = data['currentQuality']
		initCacheThread = self._checkRequestURL(data)
		
		# handle only client close
		if self._receivePlayerClose(data):
			return

		# handle only screen resolution
		if self._saveScreenResolution(data):
			return

		# handle only image data
		if self.requestURLList[-1] in 'mp4':
			pass
		else:
			self._saveImageData(data)

		metric = {}
		
		# save current client live time
		metric['time'] = (datetime.now() - serverInitTime).total_seconds()
		metric['time'] = round(metric['time'], 3)

		metric['bitrate'] = data['bitrate']

		metric['GMSD'] = self._getPQvalue()
		metric['throughput'] = self._getThroughput(data)

		# save framerate
		framerate = data['framerate'].split('/')
		if len(framerate) == 1:
			metric['framerate'] = data['framerate']
		else:
			metric['framerate'] = float(framerate[0]) / float(framerate[1])


		metric['stalling'] = self._isStalling(data)

		if len(self.metrics) == 0:
			print(f'{self._log} | {self.ip} initial bitrate: {metric["bitrate"]}')
			metric['bitrateSwitch'] = 0
			metric['totalStallingEvent'] = 0
		else:
			if metric['stalling'] == 1:
				metric['totalStallingEvent'] = self.metrics[-1]['totalStallingEvent'] + 1
			else:
				metric['totalStallingEvent'] = self.metrics[-1]['totalStallingEvent']

			if int(self.metrics[-1]['bitrate']) == int(metric['bitrate']):
				metric['bitrateSwitch'] = 0
			else:
				metric['bitrateSwitch'] = 1
				print(f'{self._log} | {self.ip} changed bitrate: {metric["bitrate"]}')

		self.rtm.metricLock.acquire()
		try:
			self.metrics.append(metric)
			if _DEBUG:
				print(f'{self._log} the client {self.ip} metric is saved: {metric}')
		except:
			print(f'{self._log} the client {self.ip} metric is not saved')
		finally:
			self.rtm.metricLock.release()
			pass