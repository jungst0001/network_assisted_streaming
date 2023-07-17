from clientData import ClientData
from cluster import ClusterAttribute, SubscriptionPlan, Cluster
import csv, time
import traceback
from datetime import datetime
from threading import Timer, Thread
import statistics, math
import sendData
import cserverConfig

from RLServerInterface import RLServerInterface

_DEBUG = True

class ControlServerHandler:
	def __init__(self, sendRLData=True, getRLResult=False, onlyMonitorQoE=False):
		self._log = '[ControlServerHandler]'

		self._serverData = None
		self._serverInitTime = datetime.now()

		self._currPlayers = []
		self._disconnPlayers = []

		# video management section
		self._video_index = cserverConfig.video_index
		self._live_streaming_server = cserverConfig.video_proxy_server
		self._live_streaming_video_name = cserverConfig.video_list[self._video_index]
		self._live_streaming_chunk_key = cserverConfig.chunk_key_list[self._video_index]
		self._live_streaming_init_key = cserverConfig.init_key_list[self._video_index]

		# cluster management section
		self._clusters = {}
		for ca in ClusterAttribute:
			self._clusters[ca.name] = {}
			for plan in SubscriptionPlan:
				if ca.name == 'HD' and plan.name == 'Premium':
					continue
				elif ca.name == 'SD' and (plan.name == 'Premium' or plan.name == 'Standard'):
					continue
				cluster = Cluster(ca, plan)
				self._clusters[ca.name][plan.name] = cluster

		# file name
		self._network_traces = ['FCC', '4G']
		self.filename = self._serverInitTime.strftime('%y%m%d_%H%M%S')
		self.filename = f'{self.filename}_{self._network_traces[cserverConfig.dataset_index]}_{self._video_index}.csv'

		# handler check tick management
		self._checkInterval = 1
		self._checkPlayerTimer = Timer(self._checkInterval, self._checkClients)
		self._checkPlayerTimer.daemon = True
		self._checkPlayerTimer.start()

		# RL data
		self._GET_RL_RESULT = getRLResult
		self._SEND_RL_DATA = sendRLData

		# RL server management section
		# self._rlInterface = RLServerInterface(self.MAX_CLIENT_NUM)

		# error metric
		self.fileWriteErrorPerClient = 0
		self.min_metric = 600
		self.min_ip = None
		self.max_metric = 0

	def getLiveStreamingInfo(self):
		return self._live_streaming_server, self._live_streaming_video_name

	def destroyPlayerHandler(self):
		print(f'{self._log} call __del__\n')
		self._checkPlayerTimer.cancel()
	
	def getServerInitTime(self):
		return self._serverInitTime

	def setCluster(self, client):
		cluster = self._clusters[client.getAttribute().name][client.getSubscriptionPlan().name]
		c_currClients = cluster.getCurrentClients()
		c_currClients.append(client)
		client.mycluster = cluster

		if len(c_currClients) == 1:
			cluster.setMaster()

	def setServerData(self, serverData):
		self._serverData = serverData

	def setClusterQuality(self, attribute, plan, quality):
		pastQuality = self._clusters[ClusterAttribute[attribute].name][SubscriptionPlan[plan].name].getClusterQualityIndex()
		self._clusters[ClusterAttribute[attribute].name][SubscriptionPlan[plan].name].setClusterQualityIndex(quality)
		print(f'{self._log} cluster: {ClusterAttribute[attribute].name} {[SubscriptionPlan[plan].name]} quality: {pastQuality} -> {quality}')

	def getQuality(self, client):
		return self.quality

	def _checkClients(self):
		# print(f'{self._log} check client')
		for p in self._currPlayers:
			if p.getAttribute() == None:
				if p.getScreenResolution()['height'] != 0:
					p.setAttribute(ClusterAttribute(p.getScreenResolution()['height']))
					p.setSubscriptionPlan(SubscriptionPlan(p.getSubscriptionPlan()))

					if _DEBUG:
						print(f'{self._log} client clustering: {p.ip} -> {p.getAttribute().name} {p.getSubscriptionPlan().name}')

					self.setCluster(p)

			if p.isDisconnected():
				self._currPlayers.remove(p)
				self._clusters[p.getAttribute().name][p.getSubscriptionPlan().name].disconnectClient(p)
				self._disconnPlayers.append(p)
				p.getTimer().cancel()
				p.setClientEndTime(datetime.now())
				print(f'{self._log} | client {p.ip} is disconnected')
		
		self._checkPlayerTimer.cancel()
		self._checkPlayerTimer = Timer(self._checkInterval, self._checkClients)
		self._checkPlayerTimer.daemon = True
		self._checkPlayerTimer.start()

	def getPlayers(self):
		return self._currPlayers

	def getPlayer(self, ip: str, port=0):
		result, player = self.isPlayer(ip)

		if result is False:
			for player in self._disconnPlayers:
				if player.ip == ip:
					print(f'{self._log} the player {ip} is already disconnected')
					return None

		if result is False:
			player = ClientData(ip, port)
			player.init_key = self._live_streaming_init_key
			player.chunk_key = self._live_streaming_chunk_key
			self._currPlayers.append(player)
			# self._clusters[player.getAttribute()].getClusterPlayers().append(player)
			print(f'{self._log} | new player {player.ip} is connected')
			print(f'{self._log} | current players is {len(self._currPlayers)}')
		else:
			player.getTimer().reset()
			
		return player

	def isPlayer(self, ip: str):
		for player in self._currPlayers:
			if player.ip == ip: 
				return True, player
		return False, None

	def terminateClientThread(self):
		for p in self._disconnPlayers:
			p.rtm.joinRequestThread()

		for p in self._currPlayers:
			p.rtm.joinRequestThread()

	def savePlayersData(self):
		self._serverData.cancelServerTimer()

		# self.terminatePlayerThread()
		f = open(f'{cserverConfig.LOCAL_DATASET_DIR}{self.filename}', 'w')
		# print(f'{self._log} curr player num is {len(self._currPlayers)}')
		# print(f'{self._log} disc player num is {len(self._disconnPlayers)}')

		for p in self._currPlayers:
			p.setClientEndTime(datetime.now())

		self._writeServerMetricInFile(f)	
		print(f'{self._log} save data of disconnPlayers')
		self._writeMetricsInFile(f, self._disconnPlayers)
		print(f'{self._log} save data of currPlayers')
		self._writeMetricsInFile(f, self._currPlayers)

		f.close()

	def _writeUtilityInFile(self, f):
		metrics = self._serverData.getServerMetrics()

		f.write(f'time,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["time"]},')
		f.write(f'{metrics[-1]["time"]}\n')

		f.write(f'utility,')
		for i in range(len(self._utility) - 1):
			f.write(f'{self._utility[i]}')
		f.write(f'{self._utility[-1]}\n')

	def _writeServerMetricInFile(self, f):
		f.write('Server Info\n')

		si = self._serverData.getServerInfo()

		f.write(f'Server CPU Core,{si["cpu_core"]}\n')
		f.write(f'Server CPU Freq,{si["cpu_freq"]}\n')
		f.write(f'Server RAM Total,{si["ram_total"]}\n')

		metrics = self._serverData.getServerMetrics()

		f.write(f'time,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["time"]},')
		f.write(f'{metrics[-1]["time"]}\n')
		
		f.write(f'Player Connected,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["connected"]},')
		f.write(f'{metrics[-1]["connected"]}\n')

		f.write(f'Throughput (KB/s),')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["throughput"]},')
		f.write(f'{metrics[-1]["throughput"]}\n')

		f.write(f'Bandwidth (KB/s),')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["bandwidth"]},')
		f.write(f'{metrics[-1]["bandwidth"]}\n')

		f.write(f'CPU Usage Percent,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["cpu_usage_percent"]},')
		f.write(f'{metrics[-1]["cpu_usage_percent"]}\n')

		f.write(f'RAM Usage Percent,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["ram_usage_percent"]},')
		f.write(f'{metrics[-1]["ram_usage_percent"]}\n')

		f.write(f'\n')

	def _writeMetricsInFile(self, f, players):
#		print(f'{self._log} [_writeMetricsInFile] players are {players}')
		total_stalling = 0
		total_bitrateSwitch = 0
		total_GMSD = 0
		slot = 0
		outlier = 0

		for p in players:
			try:
				metrics = p.getMetrics()
				tmp = f'{metrics[-1]["time"]:.3f}'

				if len(metrics) > self.max_metric:
					self.max_metric = len(metrics)

				if len(metrics) < self.min_metric and len(metrics) > 0:
					self.min_metric = len(metrics)
					self.min_ip = p.ip

				f.write(f'IP,{p.ip}\n')
				f.write(f'Attribute,{p.getAttribute()}\n')
				f.write(f'Subscription Plan,{p.getSubscriptionPlan()}\n')
				f.write(f'initTime,{p.getClientInitTime()}\n')
				f.write(f'endTime,{p.getClientEndTime()}\n')
				f.write(f'liveTime(sec),{p.getClientLiveTime().total_seconds()}\n')
				# f.write(f'startupDelay,{p.getStartupDelay()}\n')
				f.write(f'Total stalling Event,{p.getTotalStallingEvent()}\n')
				f.write(f'Total Chunk Skip Event,{p.getTotalChunkSkipEvent()}\n')
				f.write(f'client width,{p.getScreenResolution()["width"]}\n')
				f.write(f'client height,{p.getScreenResolution()["height"]}\n')

				f.write(f'time,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["time"]:.3f},')
				f.write(f'{metrics[-1]["time"]:.3f}\n')
			
				f.write(f'elapsed,')
				init = metrics[0]["time"]
				for i in range(len(metrics)-1):
					f.write(f'{(metrics[i]["time"]-init):.3f},')
				f.write(f'{(metrics[-1]["time"]-init):.3f}\n')

				f.write(f'bitrate,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["bitrate"]},')
				f.write(f'{metrics[-1]["bitrate"]}\n')
			
				f.write(f'framerate,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["framerate"]},')
				f.write(f'{metrics[-1]["framerate"]}\n')
				
				# f.write(f'bufferLevel,')
				# for i in range(len(metrics)-1):
				# 	f.write(f'{metrics[i]["bufferLevel"]},')
				# f.write(f'{metrics[-1]["bufferLevel"]}\n')

				f.write(f'master,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["master"]},')
				f.write(f'{metrics[-1]["master"]}\n')
				
				f.write(f'GMSD,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["GMSD"]},')

					if float(metrics[i]["GMSD"]) < 0.70:
						outlier += 1
						continue
					else:
						total_GMSD += float(metrics[i]["GMSD"])
				f.write(f'{metrics[-1]["GMSD"]}\n')
				# print(f'stalling Time type: {type(metrics[i]["GMSD"])}')

				if float(metrics[-1]["GMSD"]) < 0.70:
						outlier += 1
				else:
					total_GMSD += float(metrics[-1]["GMSD"])

				f.write(f'bitrateSwitch,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["bitrateSwitch"]},')
					total_bitrateSwitch += int(metrics[i]["bitrateSwitch"])
				f.write(f'{metrics[-1]["bitrateSwitch"]}\n')
				total_bitrateSwitch += int(metrics[-1]["bitrateSwitch"])

#				f.write(f'initDelayTime,')
#				for i in range(len(metrics)-1):
#					f.write(f'{metrics[i]["initDelayTime"]},')
#				f.write(f'{metrics[-1]["initDelayTime"]}\n')

				f.write(f'chunkSkip,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["chunk_skip"]},')
				f.write(f'{metrics[-1]["chunk_skip"]}\n')

				f.write(f'totalChunkSkipEvent,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["totalChunkSkipEvent"]},')
				f.write(f'{metrics[-1]["totalChunkSkipEvent"]}\n')
			
				f.write(f'stalling,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["stalling"]},')
				f.write(f'{metrics[-1]["stalling"]}\n')
			
				f.write(f'totalStallingEvent,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["totalStallingEvent"]},')
				f.write(f'{metrics[-1]["totalStallingEvent"]}\n')
				# print(f'stalling Time type: {type(metrics[-1]["stallingTime"])}')
				total_stalling += int(metrics[-1]["totalStallingEvent"])

				f.write(f'Throughput (KB/s),')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["throughput"]},')
				f.write(f'{metrics[-1]["throughput"]}\n')

				f.write(f'Latency,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["latency"]},')
				f.write(f'{metrics[-1]["latency"]}\n')

				f.write(f'QoE,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["QoE"]},')
				f.write(f'{metrics[-1]["QoE"]}\n')

				# f.write(f'TX (KBps),')
				# for i in range(len(metrics)-1):
				# 	f.write(f'{metrics[i]["tx"]},')
				# f.write(f'{metrics[-1]["tx"]}\n')

				# f.write(f'RX (KBps),')
				# for i in range(len(metrics)-1):
				# 	f.write(f'{metrics[i]["rx"]},')
				# f.write(f'{metrics[-1]["rx"]}\n')

				slot += len(metrics)

			except Exception as err:
				print(f'{self._log} file write function err: \n {traceback.format_exc()}')
				print(f'{self._log} when processing ip: {p.ip}')
				print(f'{self._log} And this metrics: {p.getMetrics()}')
				print(f'{self._log} And this resolution: {p.getScreenResolution()}')
				# print(f'{self._log} And this variable: {p.getVariable()}\n\n')
				self.fileWriteErrorPerClient += 1

			f.write(f'\n')

		if slot != 0:
			avg_GMSD = 0
			if (slot - outlier) > 0:
				avg_GMSD = total_GMSD / (slot - outlier)
			f.write(f'Avg GMSD,{avg_GMSD}\n')
			f.write(f'Total Bitrate Switch,{total_bitrateSwitch}\n')
			f.write(f'Total Stalling Event, {total_stalling}\n')
			f.write(f'\n')

			print(f'Avg GMSD,{avg_GMSD}\n')
			print(f'Total Bitrate Switch,{total_bitrateSwitch}\n')
			print(f'Total Stalling Event, {total_stalling}\n')