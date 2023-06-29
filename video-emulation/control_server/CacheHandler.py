import os
import hashlib
import subprocess
import cserverConfig
import binascii
import time
from threading import Lock

_PREP_LOCKS = {}
_LOCK_FOR_LOCK = Lock()

class CacheHandler:
	def __init__(self):
		self._log = '[CacheHandler]'
		self.localDir = cserverConfig.LOCAL_CACHE_DIR
		self._first_http = cserverConfig.FIRSTURL_CACHE_KEY

		self._urlList = []

	def _preprocessURL(self, url):
		purl = url.split('dash')
		purl = f'{self._first_http}dash{purl[1]}'

		# self._urlList.append(purl)
		# print(f'{self._log} requestURL list: {self._urlList}')

		return purl

	def _getLock(self, cacheName):
		for key in _PREP_LOCKS.keys():
			if key == cacheName:
				return _PREP_LOCKS[cacheName]

		return None

	def getMD5Hash(self, url):
		purl = self._preprocessURL(url)
		nginxCacheNameResolver = hashlib.md5()
		nginxCacheNameResolver.update(purl.encode('utf-8'))

		return nginxCacheNameResolver.hexdigest()

	# if receiving url, copy cache data to local and preprocessing the data readablly
	def initCacheData(self, url):
		cacheName = self.getMD5Hash(url)

		isFile = os.path.isfile(self.localDir + cacheName)

		if isFile is False:
			_LOCK_FOR_LOCK.acquire()
			lock = self._getLock(cacheName)
			if lock is None:
				lock = Lock()
				_PREP_LOCKS[cacheName] = lock
			_LOCK_FOR_LOCK.release()

			while lock.locked():
				time.sleep(0.2)
				if os.path.isfile(self.localDir + cacheName):
					return

			lock.acquire()
			cacheNameWithDir = f'/home/wins/jin/cache/{cacheName[-1]}/{cacheName[-3:-1]}/{cacheName}'
			self._saveCacheToLocal(cacheNameWithDir, url)
			self._preprocessCacheFile(cacheName)
			lock.release()

	def _saveCacheToLocal(self, cacheNameWithDir, url):
		# print(f'{self._log} save url in local: {url}')
		subprocess.run(['cp', cacheNameWithDir, self.localDir])
		
	def _preprocessCacheFile(self, cacheName):
		request = None
		# print(f'{self._log} search key in cache file: {cacheName}')

		with open(self.localDir + cacheName, 'rb') as file:
			data = file.read()

		# Find the index of the hex string "0d0a0d0a"
		hex_string = b'\x0d\x0a\x0d\x0a'
		index = data.find(hex_string)

		if index != -1:
			# Cut the front part and save the remaining data
			remaining_data = data[index + len(hex_string):]
			
			# Write the remaining data to a new file
			with open(self.localDir + cacheName, 'wb') as output_file:
				output_file.write(remaining_data)

		# with open(self.localDir + cacheName, 'rb+') as f:
		# 	bitstring = f.read(1)
		# 	binascii.b2a_hex(bitstring)

		# line_number = 0
		# with open(self.localDir + cacheName, encoding='ascii', errors='ignore') as f:
		# 	while True:
		# 		line = f.readline()
		# 		line_number += 1
		# 		if 'KEY' in line:
		# 			request = line.split(' ')[1].split('\n')[0]
		# 			break

		# if request is None and 'http://video_server/' in request:
		# 	print(f'{self._log} requested key does not exist')
		# 	return None
		# else:
		# 	line_number += 13 # consider last newline character
		# 	subprocess.run(['sed', '-i', f'1,{line_number}d', self.localDir + cacheName])
		# 	print(f'{self._log} cutting: {cacheName} with {line_number}')
		# subprocess.run(['truncate', '-s', '-1', self.localDir + cacheName])

		return cacheName

	def _getMP4FileFromCache(self, url):
		isFile = os.path.isfile(self.localDir + self.getMD5Hash(url))

		return isFile, self.getMD5Hash(url)

	def getChunkMP4(self, initURL, chunkURL):
		# chunkNumber = frameNumber / (chunkLengthUnit * frameRate)
		# print(f'get chunkMP4 in local cache dir:\ninitURL:{initURL}\nchunkURL:{chunkURL}')
		isInitFile, initCacheName = self._getMP4FileFromCache(initURL)
		isChunkFile, chunkCacheName = self._getMP4FileFromCache(chunkURL)

		if isInitFile and isChunkFile is False:
			print(f'{self._log} Not exist init or chunk file| init: {isInitFile}, chunk: {isChunkFile}')
			return None

		chunkMP4 = f'{self.localDir}{chunkCacheName}.mp4'

		isMP4File = os.path.isfile(chunkMP4)
		# subprocess.run(['cat', f'{self.localDir}{initCacheName}', f'{self.localDir}{chunkCacheName}', '>', chunkMP4])
		# proc = subprocess.Popen(['cat', f'{self.localDir}{initCacheName}', f'{self.localDir}{chunkCacheName}', '>', chunkMP4],
		# 	stdout=subprocess.PIPE)

		# output = proc.communicate()
		# print(output)
		if isMP4File is False:
			with open(f'{self.localDir}{initCacheName}', 'rb') as init:
				init_content = init.read() 

			with open(f'{self.localDir}{chunkCacheName}', 'rb') as chunk:
				chunk_content = chunk.read() 

			with open(f'{self.localDir}{chunkCacheName}.mp4', 'wb') as mp4:
				mp4.write(init_content + chunk_content)

		return chunkMP4

def main():
	print('Test CacheHandler fucntion')
	ch = CacheHandler()
	initURL = 'http://127.0.0.1/dash/BigBuckBunny/bunny_595491bps/BigBuckBunny_2s_init.mp4'
	chunkURL = 'http://127.0.0.1/dash/BigBuckBunny/bunny_595491bps/BigBuckBunny_2s1.m4s'

	# ch.initCacheData('http://127.0.0.1/dash/BigBuckBunny/bunny_595491bps/BigBuckBunny_2s_init.mp4')
	ch.initCacheData('http://127.0.0.1/dash/BigBuckBunny/bunny_595491bps/BigBuckBunny_2s1.m4s')
	# ch.getChunkMP4(initURL, chunkURL)

if __name__ == '__main__':
	main()