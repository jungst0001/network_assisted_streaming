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
		
		if self._ph is not None:
			self._initTime = self._ph.getServerInitTime()
		else:
			print(f'{self._log} __init__ PlayerHandler is None!!')
			self._initTime = datetime.now()

		self._checkInterval = 0.01
		self._checkServerTimer = Timer(self._checkInterval, self._checkServer)
		self._checkServerTimer.start()
#		self._checkServer()

	def cancelServerTimer(self):
		self._checkServerTimer.cancel()
		self._checkServerTimer.join()

		if self._checkServerTimer.isAlive():
			self._checkServerTimer.cancel()

	def _checkServer(self):
#		print(f'{self._log} [_checkServer] called')

		metric = {}
		# tx, rx = traffic.get_speed('ens3') # KBps this is local
		# tx, rx = traffic.get_speed_video_server() # KBps this is remote

		# temperally setting..
		tx = 0
		rx = 0
		
		if self._ph is not None:
			self._currentPlayersNum = len(self._ph.getPlayers()) 
		
		metric['time'] = (datetime.now() - self._initTime).total_seconds()
		metric['connected'] = self._currentPlayersNum
		metric['tx'] = tx
		metric['rx'] = rx
		metric['cpu_usage_percent'] = psutil.cpu_percent()
		metric['ram_usage_percent'] = psutil.virtual_memory()[2]

		self._metrics.append(metric)

		self._checkServerTimer.cancel()
		self._checkServerTimer = Timer(self._checkInterval, self._checkServer)
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
