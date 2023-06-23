import os
import argparse

def readServerInfo(slines):
	smetrics = []

	print(slines)

	time = slines[4].strip().split(',')
	playernum = slines[5].strip().split(',')
	tx = slines[6].strip().split(',')
	rx = slines[7].strip().split(',')
	cpuUsage = slines[8].strip().split(',')
	ramUsage = slines[9].strip().split(',')

	for i in range(1, len(time)):
		if float(tx[i]) + float[rx[i]) <= 40:
			continue

		metric = {}	
		metric['time'] = time[i]
		metric['connected'] = playernum[i]
		metric['tx'] = tx[i]
		metric['rx'] = rx[i]
		metric['cpu_usage_percent'] = cpuUsage[i]
		metric['ram_usage_percent'] = ramUsage[i]
		
		smetrics.append(metric)

	return smetrics

def readPlayersInfo(plines):
	# basic info 5 lines
	# metrics info 10 lines
	# empty 1 line

	try:
		pass
	except:
		pass

	pass

def readPlayerInfo(subplines):

	pmetrics = []

	pass

if __name__ == "__main__":
	print('analyzeData.py main')

	parser = argparse.ArgumentParser(description='analyze .csv')
	parser.add_argument('-r', '--read', dest='filename', type=str, help = 'python3 analyzeData.py -r DataStroage/...csv', default=None)

	args = parser.parse_args()

	if args.filename is None:
		print('input file name')

	else:
		f = open(args.filename, 'r')

		lines = f.readlines()

		f.close()

		slines = lines[:10]
		plines = lines[11:]

		smetrics = readServerInfo(slines)
	
#		for metric in smetrics:
#			print(metric['connected'])
		pmetrics = readPlayersInfo(plines)
