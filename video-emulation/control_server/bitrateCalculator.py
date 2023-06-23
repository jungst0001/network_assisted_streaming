from playerData import Player
from playerHandler import PlayerHandler
from enum import Enum, auto
from threading import Timer
from cluster import Cluster, ClusterAttribute

KBPS = 1000
CAPACITY = 5 * KBPS

class BCMethod(Enum):
	BITRATE_ONLY = auto()
	BITRATE_AND_BUFFER = auto()

class BitrateCalculator:
	def __init__(self, playerHandler: PlayerHandler, capacity: int):
		self._log = '[BitrateCalculator]'

		self._ph = playerHandler

		self._qualityIndex = {
			'bitrateHigh' : 3,
			'bitrateMedium' : 2,
			'bitrateLow' : 1
		}

		self._qualityBitrate = {
			'bitrateHigh' : 1500,
			'bitrateMedium' : 800,
			'bitrateLow' : 400
		}

		self._totalCapacity = capacity
		self._remainCapacity = self._totalCapacity
		self._usedCapacity = 0

		self._checkCapacityInterval = 3
		self._checkCapacityTimer = Timer(self._checkCapacityInterval, self._checkCapacity)
		self._checkCapacityTimer.start()

	def destroyBitrateCalculator(self):
		print(f'{self._log} call __del__')
		self._checkCapacityTimer.cancel()

	def _checkCapacity(self):
#		print(f'{self._log} [_checkCapacity] called')
		clusters = self._ph.getClusters()
		usedBitrate = 0
		
#		print(f'{self._log} [_checkCapacity] cluster is {clusters}')

		for ca in ClusterAttribute:
			self._calculateClusterBitrate(clusters[ca.name])
			usedBitrate += clusters[ca.name].getUsedBitrate()

		self._usedCapacity = usedBitrate
		self._remainCapacity = self._totalCapacity - self._usedCapacity

		self._checkCapacityTimer.cancel()
		self._checkCapacityTimer = Timer(self._checkCapacityInterval, self._checkCapacity)
		self._checkCapacityTimer.start()
	
	def _calculateUnfairness(self):
		pass

	def _calculateStalling(self):
		pass
			
	def _calculateClusterBitrate(self, cluster:Cluster):
		bitrateSum = 0
#		print(f'{self._log} [_calculateClusterBitrate] cluster is {cluster}')

		for p in cluster.getClusterPlayers():
			m = p.getCurrentMetric()
			
#			print(f'{self._log} [_calculateClusterBitrate] metric is {m}')
			if m is not None:
				pb = m['bitrate']
				bitrateSum += int(pb)

		cluster.setUsedBitrate(bitrateSum)

	def optimizeBitrate(self):
#		print(f'{self._log} optimize bitrate')
		clusters = self._ph.getClusters()

#		print(f'{self._log} {clusters}')
#		print(f'{self._ph.getClusters()[ClusterAttribute.HIGH.name]}')
		self._decideClusterQuality(self._ph.getClusters()[ClusterAttribute.HIGH.name])

	def _decideClusterQuality(self, cluster:Cluster, bcMethod=BCMethod.BITRATE_ONLY):
		totalCapacity = self._totalCapacity
		estimatedBitrate = 0

#		print(f'{self._log} {bcMethod}')
#		print(f'{self._log} {cluster.getUsedBitrate()}')
		estimatedBitrate = cluster.getUsedBitrate()

		# assign max quality
		estimatedBitrate = len(cluster.getClusterPlayers()) * self._qualityBitrate['bitrateHigh'] 

		if estimatedBitrate < totalCapacity:
			cluster.setClusterQualityIndex(self._qualityIndex['bitrateHigh'])
#			print(f'{self._log} assign high quality')
		else:
			cluster.setClusterQualityIndex(self._qualityIndex['bitrateMedium'])
#			print(f'{self._log} assign medium quality')

		
#		if method == BCMethod.BITRATE_ONLY:
#			if self._usedCapacity < self._totalCapacity:
#				cluster.setClusterQuality(self._qualityIndex['bitrateHigh'])

		pass

if __name__ == "__main__":
	LOG = '[bitrateCalculator.py main]'
	print(f'{LOG}')

	try:
		ph = PlayerHandler()
		bc = BitrateCalculator(ph, CAPACITY)

		p1 = ph.getPlayer("1.1.1.1", 10000)
		p2 = ph.getPlayer("1.1.1.2", 10000)
		p3 = ph.getPlayer("1.1.1.3", 10000)

		bc.optimizeBitrate()
		print(f'{LOG} quality is {p1.getQualityIndex()}')
		print(f'{LOG} quality is {p2.getQualityIndex()}')
		print(f'{LOG} quality is {p3.getQualityIndex()}')

		p4 = ph.getPlayer("1.1.1.4", 10000)
		p5 = ph.getPlayer("1.1.1.5", 10000)

		bc.optimizeBitrate()
		print(f'{LOG} quality is {p1.getQualityIndex()}')
		print(f'{LOG} quality is {p2.getQualityIndex()}')
		print(f'{LOG} quality is {p3.getQualityIndex()}')
		print(f'{LOG} quality is {p4.getQualityIndex()}')
		print(f'{LOG} quality is {p5.getQualityIndex()}')

	except KeyboardInterrupt:
		pass

	ph.destroyPlayerHandler()
	bc.destroyBitrateCalculator()
