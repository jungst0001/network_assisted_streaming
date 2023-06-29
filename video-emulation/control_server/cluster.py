from enum import Enum, auto

class ClusterAttribute(Enum):
	FHD = 1080
	HD = 720
	SD = 480

class Cluster:
	def __init__(self, attribute:ClusterAttribute):
		self._log = '[Cluster]'

		self.attribute = attribute
		self._currClients = []
		self._disconnClients = []

		self._qualityIndex = 3

	def getCurrentClients(self):
		return self._currClients

	def getDisconnClients(self):
		return self._disconnClients

	def setClusterQualityIndex(self, qualityIndex):
		self._qualityIndex = qualityIndex
		for clients in self._currClients:
			clients.setQualityIndex(self._qualityIndex)

	def getClusterQualityIndex(self):
		return self._qualityIndex

if __name__ == "__main__":
	LOG = '[cluster.py main]'
	print(f'{LOG}')

	for ca in ClusterAttribute:
		print(ca)
