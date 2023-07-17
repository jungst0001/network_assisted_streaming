from threading import Timer, Thread
import traffic
from datetime import datetime
import os, time, sys, math
import psutil
import cserverConfig
import paramiko
import numpy as np
import subprocess

PACKET_SIZE = 1500.0  # bytes
TIME_INTERVAL = 5.0
BITS_IN_BYTE = 8.0
MBITS_IN_BITS = 1000000.0
MBITS_TO_KBITS = 1000.0
MILLISECONDS_IN_SECONDS = 1000.0
N = 100
LTE_LINK_FILE = 'traces/belgium/logs/report_foot_0004.log'
FCC_LINK_FILE = 'traces/fcc/cooked/trace_4529613_https---www.youtube.com'

ADJUST_MIN = 0.2 * MBITS_TO_KBITS # Kbps
ADJUST_MAX = 15 * MBITS_TO_KBITS # Kbps
HOST_Scale = 1 / 1

lte_ADJUST_MIN = 0.2 * MBITS_TO_KBITS # Kbps
lte_ADJUST_MAX = 15 * MBITS_TO_KBITS # Kbps

fcc_ADJUST_MIN = 0.2 * MBITS_TO_KBITS # Kbps
fcc_ADJUST_MAX = 7 * MBITS_TO_KBITS # Kbps

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

		self.bandwidth_all = None
		self.isRunning = [True]
		self.granularity = 3
		if cserverConfig.dataset_index == 0:
			self.bandwidth_all, _ = load_fcc()
		else:
			self.bandwidth_all, _ = load_lte()

		self.bandwidth_all = np.repeat(self.bandwidth_all, self.granularity)

		# print(self.bandwidth_all)
		# self.edge_network_all = np.full((1,400), 100.0 * MBITS_TO_KBITS)[0]

		# start_traffic_shaping(cserverConfig.dataset_index, self.isRunning)
		# self.tsThread = Thread(target=self.traffic_shaping, args=(self.edge_network_all, self.isRunning, self.granularity),)
		self.vtsThrad = Thread(target=start_traffic_shaping, args=(cserverConfig.dataset_index, self.isRunning),)

		# self.tsThread.daemon = True
		self.vtsThrad.daemon = True

		# self.tsThread.start()
		self.vtsThrad.start()

		self._checkInterval = 1
		self._checkServerTimer = Timer(self._checkInterval, self._checkServer)
		self._checkServerTimer.daemon = True
		self._checkServerTimer.start()
#		self._checkServer()

	def __del__(self):
		close_traffic_shaping()
		# stop_tc()

	def traffic_shaping(self, throughpt_all, isRunning, granularity):
		bandwidth_i = 1
		set_tc(throughpt_all[bandwidth_i])

		while isRunning[0]:
			time.sleep(granularity) # default: 1sec
			bandwidth_i += 1
			change_tc(throughpt_all[bandwidth_i])

			# print(fcc_bandwidth[bandwidth_i])
			# print(lte_throughput[bandwidth_i])
			if not isRunning[0]:
				stop_tc()
				break

	def cancelServerTimer(self):
		try:
			self._checkServerTimer.cancel()
			self._checkServerTimer.join()

			if self._checkServerTimer.isAlive():
				self._checkServerTimer.cancel()
		finally:
			self.isRunning[0] = False
			close_traffic_shaping()
			# stop_tc()

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
		
		now = datetime.now()
		metric['time'] = f'{(now - self._initTime).total_seconds():.3f}'
		metric['connected'] = self._currentPlayersNum
		metric['throughput'] = f'{self.getCurrentThroughput():.3f}'
		metric['bandwidth'] = self.bandwidth_all[round((now - self._initTime).total_seconds())]
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

def load_lte():
	time_ms = []
	bytes_recv = []
	recv_time = []
	with open(LTE_LINK_FILE, 'rb') as f:
		for line in f:
			parse = line.split()
			time_ms.append(int(parse[1]))
			bytes_recv.append(float(parse[4]))
			recv_time.append(float(parse[5]))
	time_ms = np.array(time_ms)
	bytes_recv = np.array(bytes_recv)
	recv_time = np.array(recv_time)
	throughput_all = bytes_recv / recv_time

	time_ms = time_ms - time_ms[0]
	time_ms = time_ms / MILLISECONDS_IN_SECONDS
	throughput_all = throughput_all * BITS_IN_BYTE / MBITS_IN_BITS * MILLISECONDS_IN_SECONDS * MBITS_TO_KBITS

	throughput_all = adjust_throghput(throughput_all, lte_ADJUST_MIN, lte_ADJUST_MAX)

	throughput_all = throughput_all / BITS_IN_BYTE
	throughput_all = np.round(throughput_all, 3)

	return throughput_all, time_ms

def load_fcc():
	bandwidth_all = []
	with open(FCC_LINK_FILE, 'rb') as f:
		for line in f:
			throughput = int(line.split()[0])
			bandwidth_all.append(throughput)

	bandwidth_all = np.array(bandwidth_all)
	bandwidth_all = bandwidth_all * BITS_IN_BYTE / MBITS_IN_BITS * MBITS_TO_KBITS

	time_all = np.array(range(len(bandwidth_all))) * TIME_INTERVAL

	bandwidth_all = adjust_throghput(bandwidth_all, fcc_ADJUST_MIN, fcc_ADJUST_MAX)

	bandwidth_all = bandwidth_all / BITS_IN_BYTE
	bandwidth_all = np.round(bandwidth_all, 3)

	return bandwidth_all, time_all

def adjust_throghput(bandwidth_all, adj_min, adj_max):
	b_min = bandwidth_all.min()
	b_max = bandwidth_all.max()

	adj_bandwidth_all = ((bandwidth_all - b_min) / (b_max - b_min)) *\
		(adj_max - adj_min) + adj_min

	return adj_bandwidth_all

def start_traffic_shaping(dataset_index, isRunning):
	# ssh = paramiko.SSHClient()
	# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	# ssh.connect(cserverConfig.vserver_IP, port= cserverConfig.vserver_PORT, username=cserverConfig.vserver_USER, password=cserverConfig.vserver_PASSWORD)	
	# stdin, stdout, stderr = ssh.exec_command(f'cd traces && python3 trace_simulator.py -d {dataset_index} &')

	# ssh.close()

	tp = paramiko.Transport((cserverConfig.vserver_IP, cserverConfig.vserver_PORT)) # VSERVER IP
	tp.connect(username=cserverConfig.vserver_USER, password=cserverConfig.vserver_PASSWORD)

	channel = tp.open_session()
	channel.get_pty()
	channel.set_combine_stderr(1)
	channel.exec_command(f'cd traces && python3 trace_simulator.py -d {dataset_index}')

	while isRunning[0]:
		if channel.exit_status_ready():
			if channel.recv_ready():
				break
		# output = channel.recv(1024).decode(sys.stdout.encoding)
		# sys.stdout.write(output)

	print("Channel closing")
	channel.close()

def close_traffic_shaping():
	# ssh = paramiko.SSHClient()
	# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	# ssh.connect(cserverConfig.vserver_IP, port= cserverConfig.vserver_PORT, username=cserverConfig.vserver_USER, password=cserverConfig.vserver_PASSWORD)	
	
	# stdin, stdout, stderr = ssh.exec_command("cd traces && python3 trace_simulator.py -t")
	# # pid = -1

	# # stdin, stdout, stderr = ssh.exec_command("ps -ax | grep trace_simulator.py")
	# # lines = stdout.readlines()
	# # for i in range(len(lines)):
	# # 	if 'python3' in lines[i]:
	# # 		pid = lines[i].split()[0]
	# # # print(lines)
	# # print(f'current trace_simulator.py pid is {pid}')

	# # if pid != -1:
	# # 	stdin, stdout, stderr = ssh.exec_command(f'kill -2 {pid}')

	# ssh.close()

	tp = paramiko.Transport((cserverConfig.vserver_IP, cserverConfig.vserver_PORT)) # VSERVER IP
	tp.connect(username=cserverConfig.vserver_USER, password=cserverConfig.vserver_PASSWORD)

	channel = tp.open_session()
	channel.get_pty()
	channel.set_combine_stderr(1)
	channel.exec_command(f'cd traces && python3 trace_simulator.py -t')
	channel.close()

def set_tc(throughput):
	cmd = f'sudo sh tc.sh start {math.ceil(throughput * HOST_Scale)}mbit'
	p = subprocess.Popen(['sudo', '-S', 'sh', 'tc.sh', 'start', f'{math.ceil(throughput * HOST_Scale)}kbit'], 
		stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	p.stdin.write('wins2-champion\n')
	p.stdin.flush()
	prompt = p.communicate()

	# print(f'start tc with bandwidth: {math.ceil(throughput / MBITS_TO_KBITS)}mbit')

def change_tc(throughput):
	cmd = f'sudo sh tc.sh change {math.ceil(throughput * HOST_Scale)}kbit'
	out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

	# print(f'change tc with bandwidth: {math.ceil(throughput / MBITS_TO_KBITS)}mbit')

def stop_tc():
	cmd = f'sudo sh tc.sh stop'
	out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

	# print(f'stop tc')
	# print(out)

if __name__ == "__main__":
	print('ServerData.py main')
	serverData = ServerData()

	time.sleep(5)
	serverData.isRunning = [False]
	serverData.cancelServerTimer()

	print(serverData.getServerMetrics())

	# serverData.tsThread.join()