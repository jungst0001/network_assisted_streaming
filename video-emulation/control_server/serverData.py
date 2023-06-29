from threading import Timer
import traffic
from datetime import datetime
import os, time
import psutil

class ServerData:
	def __init__(self, playerHandler=None):
		self._log = '[ServerData]'

		self._ph = playerHandler

		self.serverInfo = {}
		self.serverInfo['cpu_core'] = psutil.cpu_count(logical=False)
		self.serverInfo['cpu_freq'] = f'{round(psutil.cpu_freq().max/1024, 3)} GHz'
		self.serverInfo['ram_total'] = f'{round(psutil.virtual_memory().total/1024**3)} GB'

		self._metrics = []
		self._currentPlayersNum = 0

		self._tmpMetricBox = []
		
		if self._ph is not None:
			self._initTime = self._ph.getServerInitTime()
		else:
			print(f'{self._log} __init__ PlayerHandler is None!!')
			self._initTime = datetime.now()

		self._checkInterval = 1
		self._checkServerTimer = Timer(self._checkInterval, self._checkServer)
		self._checkServerTimer.daemon = True
		self._checkServerTimer.start()
#		self._checkServer()

	def cancelServerTimer(self):
		self._checkServerTimer.cancel()
		self._checkServerTimer.join()

		if self._checkServerTimer.isAlive():
			self._checkServerTimer.cancel()

	def getCurrentThroughput(self):
		currentThroughput = 0

		if self._ph is None:
			print(f'You may do test the serverData.py, right?')
			currClients = []
		else:
			currClients = self._ph.getPlayers()

		for client in currClients:
			tmpChecker = True
			for tmpMetric in self._tmpMetricBox:
				# this means that the client in tmpbox has new throughput
				if tmpMetric[0] == client.ip:
					if tmpMetric[1] != client.getCurrentMetric():
						tmpMetric = (client.ip, client.getCurrentMetric())
						currentThroughput += float(tmpMetric[1]['throughput'])
					else:
						# this means that the client in tmpbox has past throughput.
						# so remove tmpbox to 1. decrease box size, 2. the client may already disconnect
						tmpChecker = False
						self._tmpMetricBox.remove((client.ip, client.getCurrentMetric()))
					break

			# this means that the client is new object in tmpbox
			if tmpChecker:
				if client.getCurrentMetric() is not None:
					currentThroughput += float(client.getCurrentMetric()['throughput'])
					self._tmpMetricBox.append((client.ip, client.getCurrentMetric()))

		return currentThroughput

	def _checkServer(self):
#		print(f'{self._log} [_checkServer] called')

		metric = {}
		# tx, rx = traffic.get_speed('ens3') # KBps this is local
		# tx, rx = traffic.get_speed_video_server() # KBps this is remote

		# temperally setting..
		# tx = 0
		# rx = 0
		
		if self._ph is not None:
			self._currentPlayersNum = len(self._ph.getPlayers()) 
		
		metric['time'] = f'{(datetime.now() - self._initTime).total_seconds():.3f}'
		metric['connected'] = self._currentPlayersNum
		metric['throughput'] = f'{self.getCurrentThroughput():.3f}'
		metric['cpu_usage_percent'] = psutil.cpu_percent()
		metric['ram_usage_percent'] = psutil.virtual_memory()[2]

		self._metrics.append(metric)

		self._checkServerTimer.cancel()
		self._checkServerTimer = Timer(self._checkInterval, self._checkServer)
		self._checkServerTimer.daemon = True
		self._checkServerTimer.start()

	def getServerInfo(self):
		return self.serverInfo
	
	def getServerMetrics(self):
		return self._metrics

if __name__ == "__main__":
	print('ServerData.py main')

	serverData = ServerData()

	time.sleep(3)

	print(serverData.getServerInfo())
	print(serverData.getServerMetrics())

	serverData.cancelServerTimer()
