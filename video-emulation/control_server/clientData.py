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
import traceback

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

	def getTotalStallingEvent(self):
		return self.metrics[-1]['totalStallingEvent']

	def getTotalChunkSkipEvent(self):
		return self.metrics[-1]['totalChunkSkipEvent']

	def _getInitWithChunkURL(self, frameNumber, framerate, currentQuality, chunkUnit=2):
		current_playhead = frameNumber / framerate
		chunkNumber = math.ceil(current_playhead / chunkUnit)
		print(f'{self._log} playhead: {current_playhead:.2f}, chunkNumber: {chunkNumber}')
		chunkKey = f'2s{chunkNumber}.m4s'

		initURL = None
		for init in self.initList:
			if init['quality'] == currentQuality:
				initURL = init['url']

		chunkURL = None
		checkOneMoreChunkURL = True
		while checkOneMoreChunkURL:
			# print(f'{self._log} chunklist: {self.chunkList}')
			for chunk in self.chunkList:
				if chunkKey in chunk['url']:
					if chunk['quality'] == currentQuality:
						chunkURL = chunk['url']

			if chunkURL is None:
				time.sleep(0.5)
				checkOneMoreChunkURL = False
			else:
				break

		return initURL, chunkURL

	def _getServerImageFromCache(self, frameNumber, framerate, currentQuality):
		initURL, chunkURL = self._getInitWithChunkURL(frameNumber, framerate, currentQuality)

		if (initURL is None) or (chunkURL is None):
			print(f'{self._log} {self.ip} init url or chunk url is None')
			self.chunkInCache[frameNumber] = None
			return

		chunkMP4 = self.ch.getChunkMP4(initURL, chunkURL)
		if chunkMP4 is None:
			print(f'{self._log} {self.ip} chunk mp4 with {initURL}, {chunkURL} is None')

		self.chunkInCache[frameNumber] = chunkMP4

	def _saveImageData(self, data):
		# save Image data and calculate SSIM / GMSD
		# print(f'{self._log} the client {self.ip} _saveImageData()')

		try:
			imageData = data['captured']
			bitrate = data['bitrate']
			playhead = data['playhead']

			# print(type(str(imageData)))
			# print(f'{self._log} {self.ip} image: {str(imageData)[0:20]}')

			frameNumber = imageData["frameNumber"]
			extension = imageData["type"]
			image = imageData["image"]
			framerate = self._getFrameRate(data)

			cacheThread = Thread(target=self._getServerImageFromCache, args=(frameNumber, framerate, self._currentQuality),)
			cacheThread.daemon = True
			cacheThread.start()

			self.rtm.imageLock.acquire()
			try:
				_currentFrameNumber = frameNumber
				_currentImageName = self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension

				imageInfo = (_currentImageName, _currentFrameNumber)
				self.imageList.append(imageInfo)
				
				f = open('images/' + self.ip + "-" + str(bitrate) + "-" + str(frameNumber) + '.' + extension, 'wb')
				f.write(base64.b64decode(image))
				f.close()
			finally:
				self.rtm.imageLock.release()
				pass

			if len(self.imageList) != 0:
				self.rtm.pqLock.acquire()
				try:
					head_imageInfo = self.imageList[0]
					self.imageList.remove(head_imageInfo)
					
					cacheThread.join()
					chunkMP4 = self.chunkInCache[frameNumber]
					if chunkMP4 is None:
						print(f'{self._log} chunk with frame number {frameNumber} is not cached')
						currentGMSD = 0
					else:
						currentGMSD = getClientGMSD(head_imageInfo[0], head_imageInfo[1], framerate, chunkMP4, self._currentQuality)

					print(f'{self._log} the client {self.ip} gmsd with frame number: {frameNumber} is calculated: {currentGMSD}')

					self.pqList.append((frameNumber, currentGMSD))
				except:
					print(traceback.format_exc())
					if _DEBUG:
						print(f'{self._log} the client {self.ip} gmsd is not calculated')
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
			print(f'{self._log} {self.ip} client status: {status}')

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
			self.screen_resolution = {}
			self.screen_resolution["width"] = screen_resolution["width"]
			self.screen_resolution["height"] = screen_resolution["height"]

			print(f'{self._log} | {self.ip} screen resolution: {self.screen_resolution["width"]}x{self.screen_resolution["height"]}')

			return True
		except KeyError:
			return False

	def _isStalling(self, data):
		isStalling = data['stalling']

		if isStalling == "True":
			print(f'{self._log} | {self.ip} stalling event occurs')
			return 1
		else:
			return 0

	def _getChunkSkip(self, data):
		chunk_skip_num = data['chunk_skip']

		return chunk_skip_num

	def saveClientData(self, clientData, serverInitTime):
		data = json.loads(clientData)

		requestThread = Thread(target=self._saveClientData, args=(data, serverInitTime),)

		# if _DEBUG:
		# 	print(f'{self._log} request start')

		self.rtm.requestThreadList.append(requestThread)
		requestThread.daemon = True
		requestThread.start()

		requestThread.join()
		self.rtm.requestThreadList.remove(requestThread)

		# if _DEBUG:
		# 	print(f'{self._log} request over')

	def _getPQvalue(self, frameNumber):
		pqValue = 0
		if len(self.pqList) != 0:
			if self.rtm.pqLock.acquire():
				try:
					for fn, gmsd in self.pqList:
						if fn == frameNumber:
							pqValue = gmsd
							self.pqList.remove((fn, gmsd))
				finally:
					self.rtm.pqLock.release()
					pass

		return pqValue

	# downloadRate
	def _getThroughput(self, data):
		response_length = data['response_length']
		requestInterval = data['requestInterval']

		print(f'reponse_length {response_length}, requestInterval: {requestInterval / 1000}')

		total_length = (response_length) / 1000 # make Byte to KB
		throughput = total_length / (requestInterval / 1000) # to make msec to sec

		return f'{throughput:.3f}'

	def _getFrameRate(self, data):
		framerate = 0
		if type(data['framerate']) == int:
			framerate = data['framerate']

		else:
			framerate = data['framerate'].split('/')
			if len(framerate) == 1:
				framerate = data['framerate']
			else:
				framerate = float(framerate[0]) / float(framerate[1])

		return framerate

	def _checkRequestURL(self, data):
		url = data['request_url']
		print(f'{self._log} request_url: {url}')
		self.requestURLList.append(url)
		initCacheThread = Thread(target=self.ch.initCacheData, args=(url,),)
		initCacheThread.daemon = True
		initCacheThread.start()

		if 'mp4' in url:
			currentInit = {}
			currentInit['url'] = data['request_url']
			currentInit['quality'] = data['request_url_quality']
			self.currentInit = currentInit
			self.initList.append(currentInit)

			if _DEBUG:
				print(f'{self._log} init url comm: {currentInit["url"]}')

		elif 'm4s' in url:
			currentChunk = {}
			currentChunk['url'] = data['request_url']
			currentChunk['quality'] = data['request_url_quality']
			self.currentChunk = currentChunk
			self.chunkList.append(currentChunk)

			if _DEBUG:
				print(f'{self._log} chunk url comm: {currentChunk["url"]}')

		# print(f'{self._log} initList: {self.initList}')
		# print(f'{self._log} chunkList: {self.chunkList}')

		return initCacheThread

	def _saveClientData(self, data, serverInitTime):
		# handle only screen resolution
		if self._saveScreenResolution(data):
			return

		# handle only client close
		if self._receivePlayerClose(data):
			return

		self._currentQuality = data['currentQuality']
		# print(f'{self._log} currentQuality: {self._currentQuality}')

		initCacheThread = self._checkRequestURL(data)

		# handle only image data
		initCacheThread.join()
		if 'mp4' in data['request_url']:
			pass
		else:
			self._saveImageData(data)

		metric = {}
		
		# save current client live time
		metric['time'] = (datetime.now() - serverInitTime).total_seconds()
		metric['time'] = round(metric['time'], 3)

		metric['bitrate'] = data['bitrate']

		# save perceptual quality (with GMSD)
		frameNumber = data['captured']["frameNumber"]
		metric['GMSD'] = self._getPQvalue(frameNumber)

		# save throughput (download rate)
		metric['throughput'] = self._getThroughput(data)

		# save framerate
		metric['framerate'] = self._getFrameRate(data)

		# save stalling
		metric['stalling'] = self._isStalling(data)

		# save num of chunk skip
		metric['chunk_skip'] = self._getChunkSkip(data)

		if len(self.metrics) == 0:
			print(f'{self._log} | {self.ip} initial bitrate: {metric["bitrate"]}')
			metric['bitrateSwitch'] = 0
			metric['totalStallingEvent'] = 0
			metric['totalChunkSkipEvent'] = 0
		else:
			if metric['stalling'] == 1:
				metric['totalStallingEvent'] = self.metrics[-1]['totalStallingEvent'] + 1
			else:
				metric['totalStallingEvent'] = self.metrics[-1]['totalStallingEvent']

			if metric['chunk_skip'] == 1:
				metric['totalChunkSkipEvent'] = self.metrics[-1]['totalChunkSkipEvent'] + 1
			else:
				metric['totalChunkSkipEvent'] = self.metrics[-1]['totalChunkSkipEvent']

			if int(self.metrics[-1]['bitrate']) == int(metric['bitrate']):
				metric['bitrateSwitch'] = 0
			else:
				metric['bitrateSwitch'] = 1
				print(f'{self._log} | {self.ip} changed bitrate: {metric["bitrate"]}')

		self.rtm.metricLock.acquire()
		try:
			self.metrics.append(metric)
			# if _DEBUG:
			print(f'{self._log} the client {self.ip} metric is saved: {metric}')
		except:
			print(f'{self._log} the client {self.ip} metric is not saved')
		finally:
			self.rtm.metricLock.release()
			pass