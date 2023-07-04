import numpy as np	
import subprocess
import math
import time

PACKET_SIZE = 1500.0  # bytes
TIME_INTERVAL = 5.0
BITS_IN_BYTE = 8.0
MBITS_IN_BITS = 1000000.0
MBITS_TO_KBITS = 1000.0
MILLISECONDS_IN_SECONDS = 1000.0
N = 100
LTE_LINK_FILE = './belgium/logs/report_bus_0010.log'
FCC_LINK_FILE = './fcc/cooked/trace_4529613_https---www.youtube.com'
tc_command = 'tc.sh'

HOST_Scale = 1/80
password = 'winslab'

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

	return bandwidth_all, time_all

def set_tc(throughput):
	cmd = f'sudo sh tc.sh start {math.ceil(throughput*HOST_Scale)}kbit'
	p = subprocess.Popen(['sudo', '-S', 'sh', 'tc.sh', 'start', f'{math.ceil(throughput)}Kbit'], 
		stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
	p.stdin.write('winslab\n')
	p.stdin.flush()
	prompt = p.communicate()

	print(f'start tc with bandwidth: {math.ceil(throughput)}Kbit')

def change_tc(throughput):
	cmd = f'sudo sh tc.sh change {math.ceil(throughput*HOST_Scale)}Kbit'
	out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

	print(f'change tc with bandwidth: {math.ceil(throughput)}Kbit')

def stop_tc():
	cmd = f'sudo sh tc.sh stop'
	out = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE)

	print(f'stop tc')

def main():
	lte_throughput, _ = load_lte()
	fcc_bandwidth, _ = load_fcc()

	print(len(fcc_bandwidth))
	print(len(lte_throughput))

	bandwidth_i = 0
	set_tc(fcc_bandwidth[bandwidth_i])
	try:
		while True:
			time.sleep(1)
			bandwidth_i += 1
			change_tc(fcc_bandwidth[bandwidth_i])

			# print(fcc_bandwidth[bandwidth_i])
			# print(lte_throughput[bandwidth_i])
	finally:
		stop_tc()

if __name__ == '__main__':
	main()