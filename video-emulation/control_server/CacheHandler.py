import os
import hashlib
import subprocess
import cserverConfig
import binascii
import time

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

	def getMD5Hash(self, url):
		purl = self._preprocessURL(url)
		nginxCacheNameResolver = hashlib.md5()
		nginxCacheNameResolver.update(purl.encode('utf-8'))

		return nginxCacheNameResolver.hexdigest()

	# if receiving url, copy cache data to local and preprocessing the data readablly
	def initCacheData(self, url):
		cacheName = self.getMD5Hash(url)

		cacheNameWithDir = f'/home/wins/jin/cache/{cacheName[-1]}/{cacheName[-3:-1]}/{cacheName}'
		self._saveCacheToLocal(cacheNameWithDir, url)
		self._preprocessCacheFile(cacheName)

	def _saveCacheToLocal(self, cacheNameWithDir, url):
		# print(f'{self._log} save url in local: {url}')
		subprocess.run(['cp', cacheNameWithDir, self.localDir])
		
	def _preprocessCacheFile(self, cacheName):
		request = None
		# print(f'{self._log} search key in cache file: {cacheName}')
		with open(self.localDir + cacheName, encoding='ascii', errors='ignore') as f:
			while True:
				line = f.readline()
				if 'KEY' in line:
					request = line.split(' ')[1].split('\n')[0]
					break

		if request is None :
			print(f'{self._log} requested key does not exist')
			return None
		# print(f'{self._log} preprocessing cache file: {cacheName}')
		subprocess.run(['sed', '-i', '1,16d', self.localDir + cacheName])
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
		# subprocess.run(['cat', f'{self.localDir}{initCacheName}', f'{self.localDir}{chunkCacheName}', '>', chunkMP4])
		# proc = subprocess.Popen(['cat', f'{self.localDir}{initCacheName}', f'{self.localDir}{chunkCacheName}', '>', chunkMP4],
		# 	stdout=subprocess.PIPE)

		# output = proc.communicate()
		# print(output)
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