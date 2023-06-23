from playerData import Player
from cluster import ClusterAttribute, Cluster
import csv, time
import traceback
from datetime import datetime
from threading import Timer
import statistics, math
import sendData
import cserverConfig
from multiprocessing import Process

from RLServerInterface import RLServerInterface

IP_LIST = cserverConfig.IP_LIST

NETWORK_CAPCITY = cserverConfig.NETWORK_CAPCITY 

_DEBUG = True

class PlayerHandler:
	def __init__(self, sendRLData=True, getRLResult=False, onlyMonitorQoE=False):
		self._log = '[PlayerHandler]'

		self._serverData = None

		# player management section
		self.MAX_CLIENT_NUM = cserverConfig.MAX_CLIENT_NUM
		self._currPlayers = []
		self._disconnPlayers = []

		self.isMaxPrinted = False
		self.isTmpPrinted = False

		# cluster management section
		self._clusters = {}
		for ca in ClusterAttribute:
			cluster = Cluster(ca.name)
			self._clusters[ca.name] = cluster

#		print(f'{self._log} [init] clusters: {self._clusters}')
#		self._clustering()

		self._serverInitTime = datetime.now()
		self.quality = 0
		self._initTime = datetime.now()
		self.filename = self._initTime.strftime('%y%m%d_%H%M%S.csv')
		
		self._checkInterval = 1
		self._checkPlayerTimer = Timer(self._checkInterval, self._checkPlayers)
		self._checkPlayerTimer.start()

		self.fileWriteErrorPerClient = 0
		self.min_metric = 300
		self.max_metric = 0

		self._GET_RL_RESULT = getRLResult
		self._SEND_RL_DATA = sendRLData

		# related to monitor qoe
		self._ONLY_MONITOR_QOE = onlyMonitorQoE
		self.W1_SSIM = 0.25
		# self.W2_bitrate = 1
		self.W3_switching = 0.2
		# self.W4_fairness = 1
		self.W5_stalling = 0.3
		self.W6_buffer = 0.25
		#################################

		# related to join new player
		# this is an available bitrate based on manifest file
		# 0: 400kbps, 1: 800kbps, 2: 1400kbps, 3: 2000kbps 
		self.MAX_BITRATE_RL_ACTION = 3
		self.MIN_BITRATE_RL_ACTION = 3
		self.MAX_LATEST_RL_ACTION_LEN = 3
		self.LATEST_RL_ACTION = []
		#################################
		self._rlInterface = RLServerInterface(self.MAX_CLIENT_NUM)

	def _isOKtoJoinNewPlayer():
		# isQoEDecent = self_isQoEDecrease(actions)
		# isOK = ~isQoEDecent
		isOK = True
		network_capacity = NETWORK_CAPCITY
		BITRATE = [400, 800, 1401, 2000]
		MAX_LATEST_SERVER_METRICS = 3 # unit is second
		actions = [i[0] for i in self.LATEST_RL_ACTION] # latest 3 sec actions

		current_VideoServerTx = []

		connectedPlayer = len(self._currPlayers)
		server_metrics = self._serverData.getServerMetrics()
		numofmectrics = len(server_metrics)

		## case 0: does any player join?
		if connectedPlayer == 0:
			print(f'{self._log} [_isOKtoJoinNewPlayer] any player does not join')
			return isOK

		if max(actions) == 0:
			print(f'{self._log} [_isOKtoJoinNewPlayer] ERROR: actions is 0')
			return isOK

		# prerequiste of case 1: get server state
		if numofmectrics > MAX_LATEST_SERVER_METRICS:
			current_VideoServerTx = server_metrics[-1:(-1*MAX_LATEST_SERVER_METRICS)]["tx"] # latest 3 sec
		else:
			current_VideoServerTx = server_metrics[:numofmectrics]["tx"]
		current_VideoServerTx = [i*8 for i in current_VideoServerTx]

		for i in range(len(BITRATE)):
			## case 1: RL actions is bigger than MINIMUM?
			if max(actions)-i == 0:
				print(f'{self._log} [_isOKtoJoinNewPlayer] ERROR: actions is already minimum')
				isOK = False
				break
			elif (max(actions)-i > self.MIN_BITRATE_RL_ACTION and
				network_capacity > max(current_VideoServerTx) + BITRATE[actions-i]): # based on kbit
				break
			else:
				## case 2: RL actions-1 is bigger than MINIMUM?
				if max(actions)-(i+1) > self.MIN_BITRATE_RL_ACTION:
					continue
				else:
					print(f'{self._log} [_isOKtoJoinNewPlayer] ERROR: network capacity is overflow or')
					print(f'{self._log} [_isOKtoJoinNewPlayer] \tMIN_BITRATE_RL_ACTION is reached')
					isOK = False
					break

		return isOK

	def _isQoEDecrease(actions):
		network_capacity = NETWORK_CAPCITY
		BITRATE = [400, 800, 1401, 2000]
		MAX_LATEST_SERVER_METRICS = 10 # unit is second
		MAX_LATEST_PLAYER_METRICS = 4 # unit is second (must be bigger then 2 sec)
		MIN_PINDEX = 2

		connectedPlayer = len(self._currPlayers)
		current_RLBitrate = actions

		current_Bitrate = []
		current_GMSD = []
		current_VideoServerTx = []
		current_BufferLevel = []
		current_Stalling = []
		isQoEDecrease = False

		server_metrics = self._serverData.getServerMetrics()
		numofmectrics = len(server_metrics)
		if numofmectrics == 0:
			return isQoEDecrease
		elif numofmectrics > MAX_LATEST_SERVER_METRICS:
			current_VideoServerTx = server_metrics[-1:(-1*MAX_LATEST_SERVER_METRICS)]["tx"] # latest 10 sec
		else:
			current_VideoServerTx = server_metrics[:numofmectrics]["tx"]

		## Start Simple Algorithm
		# Does overflow network_capacity when incoming a new player 
		if network_capacity > max(current_VideoServerTx) + BITRATE[actions[0]-1]:
			print(f'{self._log} [_isQoEDecrease] current network usage is not overflowed')
			isQoEDecrease = False
			return isQoEDecrease
		# 1. On the current context, does the QoE being degraded?
		# -> the result of RLServer can be used.
		# 2. if incoming a new player, does the QoE be expected?
		# Other. Using reward function?
		else:
			# pindex is max of metrics
			# mindex is min of current metrics but bigger than MIN_PINDEX
			pindex = MAX_LATEST_PLAYER_METRICS / 2 # collecting frequency is 2 sec
			mindex = pindex

			for p in self._currPlayers:
				pmetrics = p.getMetrics()
				if len(metrics) < MIN_PINDEX:
					print(f'{self._log} [_isQoEDecrease] pindex is smaller')
					continue
				# elif len(metrics) < pindex:
				# 	metrics = pmetrics[-1:(-1*len(pmetrics))]
				# 	if len(metrics) < mindex:
				# 		mindex = len(metrics)
				else:
					metrics = pmetrics[-1:(-1*pindex)]
				
				# the latest info close to index: 0
				# matrix c x r: num_of_currPlayer x mindex 
				# current algorithm is working as : num_of_currPlayer x 2 
				current_Bitrate.append(metrics["bitrate"])
				current_GMSD.append(metrics["GMSD"])
				current_BufferLevel.append(metrics["bufferLevel"])
				current_Stalling.append(metrics["stalling"])

			## case 1: pindex is over 2 -> rate of decent
			# how to: consider a relation of avg bitrate and avg bufferlevel
			avg_bitrates = []
			avg_bufferLevel = []
			avg_gmsd = []
			is_stalling = []
			br = 0
			bl = 0
			ss = 0
			st = 0
			for i in range(mindex):
				for p in range(len(current_Bitrate)):
					br += current_Bitrate[p][i]
					bl += current_BufferLevel[p][i]
					ss += current_SSIM[p][i]
					st += current_Stalling[p][i]
				avg_bitrates.append(br)
				avg_bufferLevel.append(bl)
				avg_ssim.append(ss)
				is_stalling.append(st)
				br = 0
				bl = 0
				ss = 0
				st = 0

			# case 2: 

		return isQoEDecrease

	def getInitTime(self):
		return self._initTime

	def setServerData(self, serverData):
		self._serverData = serverData

	def destroyPlayerHandler(self):
		print(f'{self._log} call __del__\n')
		self._checkPlayerTimer.cancel()
		
		for p in self._currPlayers:
			p.getTimer().cancel()

	def getServerInitTime(self):
		return self._serverInitTime

	def _clustering(self):
		for p in self._currPlayers:
			self._clusters[p.getAttribute()].getClusterPlayers().append(p)

	def getClusters(self):
		return self._clusters

	def _calculateBitrateBasedOnQoE(self):
		# QUALITY_INDEX = [0, 1, 2, 3]

		# network_capacity = NETWORK_CAPCITY
		# network_tx = float(self._serverData.getServerMetrics()[-1]['tx']) * 8
		# network_rx = float(self._serverData.getServerMetrics()[-1]['rx']) * 8
		# network_tx_rx = network_tx + network_rx

		# current_player_bitrates = []
		# current_player_rx = []

		# for p in self._currPlayers:
		# 	metrics = p.getMetrics()
		# 	current_player_bitrates.append(float(metrics[-1]['bitrate']))
		# 	current_player_rx.append(float(metrics[-1]['rx']) * 8) # rx is bytes

		# current_network_throughput = sum(current_bitrates) + sum(current_rx)

		# SSIM과 client의 network 입출입 고려
		current_utility = self._calculateCurrentUtility()

		next_utility = []
		BITRATE = [400, 800, 1401, 2000]
		for b in BITRATE:
			next_utility.append(self._calculateBitrateUtility(b))

		print(f'{self._log} [_calculateBitrateBasedOnQoE] current_utility: {current_utility}')
		print(f'{self._log} [_calculateBitrateBasedOnQoE] next_utility: {next_utility}')

		index_number = -1 # max bitrate index
		for i in range(len(next_utility)):
			max_utility = max(next_utility)
			if max_utility > current_utility:
				index_number = next_utility.index(max_utility)
			else:
				next_utility[next_utility.index(max_utility)] = 0

		if index_number == -1: # if current utility is the most bigger one
			tmp = max(next_utility)
			index_number = next_utility.index(tmp)

		optimal_quality_number = index_number

		isCurrentUtility = True
		if current_utility == 0:
			isCurrentUtility = False

		return optimal_quality_number, isCurrentUtility

	def _checkPlayers(self):
#		print(f'{self._log} [_checkPlayers] called')
#		print(f'{self._log} running _checkPlayers')
		current_bitrates = []

		bitrate_count = 0
		for p in self._currPlayers:
			metrics = p.getMetrics()
			if len(metrics) != 0:
				current_bitrates.append(float(metrics[-1]['bitrate']))

				# if float(metrics[-1]['bitrate']) == 2000:
				# 	bitrate_count += 1
				# elif float(metrics[-1]['bitrate']) == 1401:
				# 	bitrate_count += 1
				# elif float(metrics[-1]['bitrate']) == 800:
				# 	bitrate_count += 1
				# elif float(metrics[-1]['bitrate']) == 400:
				# 	bitrate_count += 1

		if len(self._currPlayers) >= 25 and len(self._currPlayers) == len(current_bitrates):
			if self.isMaxPrinted is False and len(set(current_bitrates)) == 1:
				print(f'{self._log} all players have equal quality: {math.floor(current_bitrates[-1])}')
				self.isMaxPrinted = True
			elif len(set(current_bitrates)) > 1:
				self.isMaxPrinted = False

		if len(current_bitrates) > 0:
			fairness = 0
			mean = statistics.mean(current_bitrates)
			for b in current_bitrates:
				fairness += abs(b) - mean
#			print(f'{self._log} current bitrate fairness is {fairness}')

		if self._ONLY_MONITOR_QOE is True:
			self._getQoEQuality()
		else:
			if self._GET_RL_RESULT is True:
				self._getRLQuality()

		# if bitrate_count >= 5 and bitrate_count == len(self._currPlayers):
		# 	if self.isMaxPrinted is False:
		# 		print(f'{self._log} all players have equal quality: {math.floor(current_bitrates[-1])}')
		# 		self.isMaxPrinted = True

		for p in self._currPlayers:
			if p.isDisconnected():
				self._currPlayers.remove(p)
				self._clusters[p.getAttribute()].getClusterPlayers().remove(p)
				self._disconnPlayers.append(p)
				p.getTimer().cancel()
				print(f'{self._log} | player {p.ip} is disconnected')
#				print(f'{self._log} current player num is {len(self._currPlayers)}')
		
		self._checkPlayerTimer.cancel()
		self._checkPlayerTimer = Timer(self._checkInterval, self._checkPlayers)
		self._checkPlayerTimer.start()

	# should be updated
	def setQuality(self, quality):
		self.quality = quality

	def _getQoEQuality(self):
		"""
		알고리즘 설명:
		현재 상태의 SSIM을 포함한 utility 계산
		현재 상태에서 다른 bitrate를 골랐을 때, utility 계산 (미래상태)
		이 때 이론상 maxSSIM 값을 넣음
		가장 높은 utility값을 선택 (greedy algorithm)
		"""

		optimal_quality, isCurrentUtility = self._calculateBitrateBasedOnQoE()

		if isCurrentUtility is True:
			for i in range(self.MAX_CLIENT_NUM):
				for p in self._currPlayers:
					if IP_LIST[i] == p.ip:
						print(f'{self._log} [_getQoEQuality] setting quality: {p.ip}/{optimal_quality}')
						p.setQualityIndex(optimal_quality)
						
						break

	def _getRLQuality(self):
		# print(f'{self._log} [_getRLQuality] start function')
		currentState = self._rlInterface.progressData(self._currPlayers,
			self._serverData.getServerMetrics())

		if currentState is None:
			# print(f'{self._log} [_getRLQuality] currentState is None.')
			return

		# client_state = currentState['client']
		# for i in range(5):
		# 	if float(client_state[i]['SSIM']) != 0 and float(client_state[i]['SSIM']) < 0.7:
		# 		print(f'{self._log} [_getRLQuality] SSIM is outlier.')
		# 		return

		actions = self._rlInterface.sendCurrentState(currentState)

		## This part decides whether a new client join is allowed
		## and Deprecated
		if len(self.LATEST_RL_ACTION) < self.MAX_LATEST_RL_ACTION_LEN:
			self.LATEST_RL_ACTION.insert(0, actions)
		else:
			self.LATEST_RL_ACTION.pop()
			self.LATEST_RL_ACTION.insert(0, actions)

		## rl quality tracking
		for i in range(self.MAX_CLIENT_NUM):
			for p in self._currPlayers:
				post_ip = p.ip.split('.')[-1]
				if i == int(post_ip) - 1:
					if actions[i] == 0:
						# print(f'{self._log} [_getRLQuality] actions have a issue')
						# p.setQualityIndex(0)
						pass
					else:
						# print(f'{self._log} [_getRLQuality] setting quality: {p.ip}/{actions[i] - 1}')
						p.setQualityIndex(actions[i] - 1)
					
					break

	# should be updated
	def getQuality(self):
		return self.quality

	def getPlayers(self):
		return self._currPlayers

	def getPlayer(self, ip: str, port=0):
		result, player = self.isPlayer(ip)
#		print(f'{self._log} self.isPlayer result is {result}')
		if result is False:
			for player in self._disconnPlayers:
				if player.ip == ip:
					print(f'{self._log} the player {ip} is already disconnected')
					return None

		if result is False:
			player = Player(ip, port)
			self._currPlayers.append(player)
			self._clusters[player.getAttribute()].getClusterPlayers().append(player)
#			print(f'{type(self._clusters[player.getAttribute()].getClusterPlayers())}')
			print(f'{self._log} | new player {player.ip} is connected')
			print(f'{self._log} | current players is {len(self._currPlayers)}')
			
			return player
		else:
#			print(f'{self._log} the player {player.ip} is searched')
			player.getTimer().reset()

			return player

	def isPlayer(self, ip: str):
		for player in self._currPlayers:
			#print(f'{self._log} the player ip is {player.ip} and received ip is {ip}')
			if player.ip == ip: 
				return True, player
		return False, None

	def terminatePlayerProcess(self):
		for p in self._disconnPlayers:
			for saveProcess in p.processList:
				if saveProcess.is_alive():
					saveProcess.join()

		for p in self._currPlayers:
			for saveProcess in p.processList:
				if saveProcess.is_alive():
					saveProcess.join()

	def tmp_waitPlayerToBeDisconn(self):
		while True:
			print(f'wait players to be disconnected: {len(self._currPlayers)}')
			if len(self._currPlayers) <= 0:
				break

			time.sleep(1)

	def savePlayersData(self):
		self._serverData.cancelServerTimer()

		# self.terminatePlayerProcess()

		f = open('DataStorage/' + self.filename, 'w')
		# print(f'{self._log} curr player num is {len(self._currPlayers)}')
		# print(f'{self._log} disc player num is {len(self._disconnPlayers)}')

		for p in self._currPlayers:
			p.setPlayerEndTime(datetime.now())

		self._writeServerMetricInFile(f)	
		print(f'{self._log} save data of disconnPlayers')
		self._writeMetricsInFile(f, self._disconnPlayers)
		print(f'{self._log} save data of currPlayers')
		self._writeMetricsInFile(f, self._currPlayers)

		f.close()

		if self._SEND_RL_DATA:
			print(f'{self._log} send file to RL server')
			sendData.sendFileToRLServer(self.filename)

		# if self._IS_UTILITY:
		# 	f = open('UtilityFunc/' + 'u_' + self.filename, 'w')
		# 	self._writeUtilityInFile(f)
		# 	f.close()

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
			f.write(f'{metrics[i]["time"]:.3f},')
		f.write(f'{metrics[-1]["time"]:.3f}\n')
		
		f.write(f'Player Connected,')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["connected"]},')
		f.write(f'{metrics[-1]["connected"]}\n')

		f.write(f'TX (Kbps),')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["tx"]},')
		f.write(f'{metrics[-1]["tx"]}\n')

		f.write(f'RX (Kbps),')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["rx"]},')
		f.write(f'{metrics[-1]["rx"]}\n')

		f.write(f'TX + RX (Kbps),')
		for i in range(len(metrics)-1):
			f.write(f'{metrics[i]["tx"] + metrics[i]["rx"]},')
		f.write(f'{metrics[-1]["tx"] + metrics[-1]["rx"]}\n')

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

				f.write(f'IP,{p.ip}\n')
				f.write(f'Attribute,{p.getAttribute()}\n')
				f.write(f'initTime,{p.getPlayerInitTime()}\n')
				f.write(f'endTime,{p.getPlayerEndTime()}\n')
				f.write(f'liveTime(sec),{p.getPlayerLiveTime().total_seconds()}\n')
				f.write(f'startupDelay,{p.getStartupDelay()}\n')
				f.write(f'Total stalling Event,{p.getStallingEvent()}\n')
				f.write(f'player width,{p.getPlayerResolution()["width"]}\n')
				f.write(f'player height,{p.getPlayerResolution()["height"]}\n')

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
				
				f.write(f'bufferLevel,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["bufferLevel"]},')
				f.write(f'{metrics[-1]["bufferLevel"]}\n')
				
				f.write(f'GMSD,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["GMSD"]},')

					if float(metrics[i]["GMSD"]) < 0.75:
						outlier += 1
						continue
					else:
						total_GMSD += float(metrics[i]["GMSD"])
				f.write(f'{metrics[-1]["GMSD"]}\n')
				# print(f'stalling Time type: {type(metrics[i]["GMSD"])}')

				if float(metrics[-1]["GMSD"]) < 0.75:
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
			
				f.write(f'stalling,')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["stalling"]},')
				f.write(f'{metrics[-1]["stalling"]}\n')
			
				f.write(f'stallingTime (sec),')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["stallingTime"]},')
				f.write(f'{metrics[-1]["stallingTime"]}\n')
				# print(f'stalling Time type: {type(metrics[-1]["stallingTime"])}')
				total_stalling += int(metrics[-1]["stallingTime"])

				f.write(f'Throughput (Kbps),')
				for i in range(len(metrics)-1):
					f.write(f'{metrics[i]["throughput"]},')
				f.write(f'{metrics[-1]["throughput"]}\n')

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
				print(f'{self._log} And this resolution: {p.getPlayerResolution()}')
				print(f'{self._log} And this variable: {p.getVariable()}\n\n')
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

if __name__ == "__main__":
	print('playerHandler.py main')

	ph = PlayerHandler()

	ip = "127.0.0.1"
	ph.getPlayer(ip)

	print(ph.filename)

	time.sleep(5)

