from enum import Enum, auto

class SubscriptionPlan(Enum):
	Premium = 1
	Standard = 2
	Basic = 3

class ClusterAttribute(Enum):
	FHD = 1080
	HD = 720
	SD = 480

class WeightedParameter(Enum):
	w1 = 1 # bitrate
	w2 = 1 # gmsd
	w3 = 1 # bitrate switch
	w4 = 1 # latency
	w5 = 1.2 # rebuffering
	w6 = 1.4 # chunk skip

	cluster_FHD = 1
	cluster_HD = 1.2
	cluster_SD = 1.5

class Cluster:
	def __init__(self, attribute:ClusterAttribute, plan:SubscriptionPlan):
		self._log = '[Cluster]'

		self.plan = plan
		self.attribute = attribute
		self.cluster_parameter = 0

		if attribute.name == 'FHD':
			self.cluster_parameter = WeightedParameter.cluster_FHD.value
		elif attribute.name == 'HD':
			self.cluster_parameter = WeightedParameter.cluster_HD.value
		elif attribute.name == 'SD':
			self.cluster_parameter = WeightedParameter.cluster_SD.value

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

	def getUtilityFunction(self):
		pass

	def setMasterGMSD(self, gmsd):
		for client in self._currClients:
			client.setMasterGMSD(gmsd)

	def disconnectClient(self, client):
		self._currClients.remove(client)
		self._disconnClients.append(client)

		if client.isMaster == True:
			client.isMaster = False
			self.setMaster()

	def setMaster(self):
		if len(self._currClients) >= 1:
			self._currClients[0].isMaster = True
			print(f'{self._log} | [INFO] {self._currClients[0].ip} is master')

if __name__ == "__main__":
	LOG = '[cluster.py main]'
	print(f'{LOG}')

	for ca in ClusterAttribute:
		print(ca)
