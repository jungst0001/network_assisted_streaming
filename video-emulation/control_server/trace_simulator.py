import numpy as np	
import subprocess
import argparse
import math
import time

PACKET_SIZE = 1500.0  # bytes
TIME_INTERVAL = 5.0
BITS_IN_BYTE = 8.0
MBITS_IN_BITS = 1000000.0
MBITS_TO_KBITS = 1000.0
MILLISECONDS_IN_SECONDS = 1000.0
N = 100
LTE_LINK_FILE = './belgium/logs/report_foot_0001.log'
FCC_LINK_FILE = './fcc/cooked/trace_4529613_https---www.youtube.com'
tc_command = 'tc.sh'

ADJUST_MIN = 0.2 * MBITS_TO_KBITS # Kbps
ADJUST_MAX = 6 * MBITS_TO_KBITS # Kbps

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

	throughput_all = adjust_throghput(throughput_all)

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

	bandwidth_all = adjust_throghput(bandwidth_all)

	return bandwidth_all, time_all

def adjust_throghput(bandwidth_all):
	b_min = bandwidth_all.min()
	b_max = bandwidth_all.max()

	adj_bandwidth_all = ((bandwidth_all - b_min) / (b_max - b_min)) *\
		(ADJUST_MAX - ADJUST_MIN) + ADJUST_MIN

	return adj_bandwidth_all

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

def shuffle_throughput(throughpt_all):
	np.random.shuffle(throughpt_all)

	return throughpt_all

def traffic_shaping(throughpt_all, granularity=1):
	bandwidth_i = 0
	set_tc(throughpt_all[bandwidth_i])
	try:
		while True:
			time.sleep(granularity) # default: 1sec
			bandwidth_i += 1
			change_tc(throughpt_all[bandwidth_i])

			# print(fcc_bandwidth[bandwidth_i])
			# print(lte_throughput[bandwidth_i])
	finally:
		stop_tc()


def test():
	lte_throughput, _ = load_lte()
	fcc_bandwidth, _ = load_fcc()

	# print(len(fcc_bandwidth))
	# print(len(lte_throughput))

	bandwidth_i = 0

	lte_throughput = shuffle_throughput(lte_throughput)
	fcc_bandwidth = shuffle_throughput(fcc_bandwidth)

	set_tc(lte_throughput[bandwidth_i])
	try:
		while True:
			time.sleep(1)
			bandwidth_i += 1
			change_tc(lte_throughput[bandwidth_i])

			# print(fcc_bandwidth[bandwidth_i])
			# print(lte_throughput[bandwidth_i])
	finally:
		stop_tc()

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('-d', '--dataset', dest='dataset', help='select dataset', type=int, default=None)
	args = parser.parse_args()

	if args.dataset == None:
		print(f'select dataset number, fcc:0, belgium:1')
		
		exit()

	throughpt_all = None
	if args.dataset == 0:
		throughpt_all, _ = load_fcc()
	elif args.dataset == 1:
		throughpt_all, _ = load_lte()

	# throughpt_all = shuffle_throughput(throughpt_all)
	traffic_shaping(throughpt_all, granularity=1)