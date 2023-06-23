from enum import Enum, auto

class ClusterAttribute(Enum):
	HIGH = auto()
	MEDIUM = auto()
	LOW = auto()

class Cluster:
	def __init__(self, attribute:ClusterAttribute):
		self._log = '[Cluster]'

		self.attribute = attribute
		self._players = []

		self._usedBitrate = 0
		self._qualityIndex = 0

	def getClusterPlayers(self):
		return self._players

	def setClusterQualityIndex(self, qualityIndex):
		self._qualityIndex = qualityIndex
		for p in self._players:
			p.setQualityIndex(self._qualityIndex)

	def getClusterQualityIndex(self):
		return self._qualityIndex

	def setUsedBitrate(self, usedBitrate):
		self._usedBitrate = usedBitrate

	def getUsedBitrate(self):
		return self._usedBitrate

if __name__ == "__main__":
	LOG = '[cluster.py main]'
	print(f'{LOG}')

	for ca in ClusterAttribute:
		print(ca)
