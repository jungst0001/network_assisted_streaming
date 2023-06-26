import os
import hashlib
import subprocess
import cserverConfig

class CacheHandler:
	def __init__(self):
		self._log = '[CacheHandler]'
		self.localDir = cserverConfig.LOCAL_CACHE_DIR

		self._nginxCacheNameResolver = hashlib.md5()

	def getMD5Hash(self, url)
		self._nginxCacheNameResolver.update(url)

		return self._nginxCacheNameResolver.hexdigest()

	# if receiving url, copy cache data to local and preprocessing the data readablly
	def initCacheData(self, url):
		cacheName = self.getMD5Hash(url)

		cacheNameWithDir = f'../../{cacheMd5[-1]}/{cacheMd5[-3:-1]}/{cacheMd5}'
		self._saveCacheToLocal(cacheNameWithDir)
		self._preprocessCacheFile(cacheName)

	def _saveCacheToLocal(self, cacheNameWithDir):
		subprocess.run(['cp', cacheNameWithDir, self.localDir])

	def _preprocessCacheFile(self, cacheName):
		request = None
		with open(self.localDir + cacheName) as f:
			line = f.readline()
			if line in 'KEY':
				request = line.split()[1]
				break

		if request is not None and request in 'init':
			self.initDict[request] = cacheName

		subprocess.run(['sed', '-i', '\'1,16d\'', self.localDir + cacheName])
		subprocess.run(['truncate', '-s', '-1', self.localDir + cacheName])

		return cacheName

	def _getMP4FileFromCache(self, url):
		isFile = os.path.isfile(self.LOCAL_CACHE_DIR + self.getMD5Hash(url))

		return isFile, self.getMD5Hash(url)

	def getChunkMP4(self, initURL, chunkURL):
		# chunkNumber = frameNumber / (chunkLengthUnit * frameRate)

		isInitFile, initCacheName = self._getMP4FileFromCache(initURL)
		isChunkFile, chunkCacheName = self._getMP4FileFromCache(chunkURL)

		if isInitFile and isChunkFile is False:
			print(f'{self._log} Not exist init or chunk file| init: {isInitFile}, chunk: {isChunkFile}')
			return None

		chunkMP4 = f'{self.localDir}{chunkCacheName}.mp4'
		subprocess.run(['cat', initCacheName, chunkCacheName, '>', chunkMP4])

		return chunkMP4

def main():
	print('Test CacheHandler fucntion')
	CacheHandler = CacheHandler()


if __name__ == '__main__':
	main()