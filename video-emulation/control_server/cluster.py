from enum import Enum, auto

class SubscriptionPlan(Enum):
	Premium = 1
	Standard = 2
	Basic = 3

class ClusterAttribute(Enum):
	FHD = 1080
	HD = 720
	SD = 480

class Cluster:
	def __init__(self, attribute:ClusterAttribute, plan:SubscriptionPlan):
		self._log = '[Cluster]'

		self.plan = plan
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

	def disconnectClient(self, client):
		self._currClients.remove(client)
		self._disconnClients.append(client)

		if client.isMaster == True:
			client.isMaster = False
			self.setMaster()

	def setMaster(self):
		if len(self._currClients) >= 1:
			self._currClients[0].isMaster = True

if __name__ == "__main__":
	LOG = '[cluster.py main]'
	print(f'{LOG}')

	for ca in ClusterAttribute:
		print(ca)
