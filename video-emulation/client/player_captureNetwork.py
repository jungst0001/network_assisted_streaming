from scapy.all import *
import psutil
from collections import defaultdict
import os
from threading import Thread
import pandas as pd
import time
import player_generator
import json
import requests

# get the all network adapter's MAC addresses
all_macs = {iface.mac for iface in ifaces.values()}
# A dictionary to map each connection to its correponding process ID (PID)
connection2pid = {}
pid2fname = {}
# A dictionary to map each process ID (PID) to total Upload (0) and Download (1) traffic
pid2traffic = defaultdict(lambda: [0, 0])
# the global Pandas DataFrame that's used to track previous traffic stats
global_df = None
# global boolean for status of the program
is_program_running = True

MONITORING_INTERVAL = 1 # unit is second
pList = []
LOG_LEVEL = "DEBUG" # or "INFO"
_LOG = "player_captureNetwork.py"

def get_size(bytes):
	"""
	Returns size of bytes in a nice format
	"""
	for unit in ['', 'K', 'M', 'G', 'T', 'P']:
		if bytes < 1024:
			return f"{bytes:.2f}{unit}B"
		bytes /= 1024

def process_packet(packet):
	global pid2traffic
	try:
		# get the packet source & destination IP addresses and ports
		packet_connection = (packet.sport, packet.dport)
	except (AttributeError, IndexError):
		# sometimes the packet does not have TCP/UDP layers, we just ignore these packets
		pass
	else:
		# get the PID responsible for this connection from our `connection2pid` global dictionary
		packet_pid = connection2pid.get(packet_connection)

		if packet_pid:
			if packet.src in all_macs:
				# the source MAC address of the packet is our MAC address
				# so it's an outgoing packet, meaning it's upload
				pid2traffic[packet_pid][0] += len(packet)
			else:
				# incoming packet, download
				pid2traffic[packet_pid][1] += len(packet)

def get_connections():
	"""A function that keeps listening for connections on this machine 
	and adds them to `connection2pid` global variable"""
	global connection2pid
	while is_program_running:
		# using psutil, we can grab each connection's source and destination ports
		# and their process ID
		for c in psutil.net_connections():
			if c.laddr and c.raddr and c.pid:
				# if local address, remote address and PID are in the connection
				# add them to our global dictionary
				if c.raddr.ip in player_generator.MSERVER_URL:
					connection2pid[(c.laddr.port, c.raddr.port)] = c.pid
					connection2pid[(c.raddr.port, c.laddr.port)] = c.pid
					if LOG_LEVEL == "DEBUG":
						print(c)
		# sleep for a second, feel free to adjust this
		time.sleep(MONITORING_INTERVAL)

def print_pid2traffic():
	global global_df
	# initialize the list of processes
	processes = []
	for pid, traffic in pid2traffic.items():
		# `pid` is an integer that represents the process ID
		# `traffic` is a list of two values: total Upload and Download size in bytes
		try:
			# get the process object from psutil
			p = psutil.Process(pid)
		except psutil.NoSuchProcess:
			# if process is not found, simply continue to the next PID for now
			continue
		# get the name of the process, such as chrome.exe, etc.
		name = p.name()
		# get the time the process was spawned
		try:
			create_time = datetime.fromtimestamp(p.create_time())
		except OSError:
			# system processes, using boot time instead
			create_time = datetime.fromtimestamp(psutil.boot_time())
		# construct our dictionary that stores process info
		process = {
			"pid": pid, "name": name, "create_time": create_time, "Upload": traffic[0],
			"Download": traffic[1],
		}
		try:
			# calculate the upload and download speeds by simply subtracting the old stats from the new stats
			process["Upload Speed"] = traffic[0] - global_df.at[pid, "Upload"]
			process["Download Speed"] = traffic[1] - global_df.at[pid, "Download"]
		except (KeyError, AttributeError):
			# If it's the first time running this function, then the speed is the current traffic
			# You can think of it as if old traffic is 0
			process["Upload Speed"] = traffic[0]
			process["Download Speed"] = traffic[1]
		# append the process to our processes list
		processes.append(process)

	# construct our Pandas DataFrame
	df = pd.DataFrame(processes)
	try:
		# set the PID as the index of the dataframe
		df = df.set_index("pid")
		# sort by column, feel free to edit this column
		df.sort_values("Download", inplace=True, ascending=False)
	except KeyError as e:
		# when dataframe is empty
		pass
	# make another copy of the dataframe just for fancy printing
	printing_df = df.copy()
	try:
		# apply the function get_size to scale the stats like '532.6KB/s', etc.
		printing_df["Download"] = printing_df["Download"].apply(get_size)
		printing_df["Upload"] = printing_df["Upload"].apply(get_size)
		printing_df["Download Speed"] = printing_df["Download Speed"].apply(get_size).apply(lambda s: f"{s}/s")
		printing_df["Upload Speed"] = printing_df["Upload Speed"].apply(get_size).apply(lambda s: f"{s}/s")
	except KeyError as e:
		# when dataframe is empty again
		pass
	# clear the screen based on your OS
	# os.system("cls") if "nt" in os.name else os.system("clear")
	# print our dataframe
	print(printing_df.to_string())
	# update the global df to our dataframe
	global_df = df

def print_stats():
	"""Simple function that keeps printing the stats"""
	while is_program_running:
		time.sleep(MONITORING_INTERVAL)
		print_pid2traffic()

###########################################

def threaded_sniff():
	sniff(prn=process_packet, store=False)

def setCaptureProcess(pidList):
	global connection2pid
	pList = []

	for pid in pidList:
		try:
			pList.append(psutil.Process(pid))
			for conn in pList[-1].connections():
				if conn.raddr in player_generator.MSERVER_URL:
					connection2pid[(conn.laddr.port, conn.raddr.port)] = pid
					connection2pid[(conn.raddr.port, conn.laddr.port)] = pid
		except psutil.NoSuchProcess:
			if LOG_LEVEL == "DEBUG":
				print(f'{_LOG} There is no such process: {pid}')
			continue
		except psutil.AccessDenied:
			print(f'{_LOG} Run as root privilege')
			exit(0)

def startPlayersMonitoring():
	# start the printing thread
	printing_thread = Thread(target=print_stats)
	printing_thread.start()

	# start the get_connections() function to update the current connections of this machine
	connections_thread = Thread(target=get_connections)
	connections_thread.start()

	# setCaptureProcess(pidList)
	# sniff(prn=process_packet, store=False)
	sniff_thread = Thread(target=threaded_sniff)
	sniff_thread.start()

def stopPlayersMonitoring():
	global is_program_running
	is_program_running = False

def matchingPIDtoPlayer(p2f):
	global pid2fname
	# player pid to player name maching and can be stored in control server
	# use guide: pid2fname[(pid)] returns fname
	pid2fname = p2f

	if LOG_LEVEL == "DEBUG":
		print(f'{_LOG} pid2fname is registered (total length: {len(pid2fname)})')
		print(f'{_LOG} {pid2fname}')

def sendingMonitoringData(data):
	# sending data to contorl server
	res = requests.post(player_generator.CSERVER, data=data)

	if LOG_LEVEL == "DEBUG":
		print(f'{_LOG} send to CSERVER data. data:\n{data}')

def main():
	global is_program_running

	# start the printing thread
	printing_thread = Thread(target=print_stats)
	printing_thread.start()

	# start the get_connections() function to update the current connections of this machine
	# connections_thread = Thread(target=get_connections)
	# connections_thread.start()

	# start sniffing
	print(f"{_LOG} Started sniffing")
	sniff(prn=process_packet, store=False)
	# setting the global variable to False to exit the program
	is_program_running = False   

if __name__ == "__main__":
	main()
	