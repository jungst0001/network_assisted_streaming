import os

_log = '[getSummary.py]'

def readObservation(filename, subDir=None):
	if subDir is None:
		f = open('DataStorage/' + filename, 'r')
	else:
		f = open('DataStorage/' + subDir + filename, 'r')

	while True:
		line = f.readline()
		if not line: break
		line = line.split('\n')[0].split(',')

		if line[0] == "Avg GMSD":
			avg_GMSD = line[1]
			continue
		elif line[0] == "Total Bitrate Switch":
			total_Bitrate = line[1]
			continue
		elif line[0] == "Total Stalling Event":
			total_Stalling = line[1]
			continue

	f.close()

	return avg_GMSD, total_Bitrate, total_Stalling

def checkDataStorage(subDir=None):
	if subDir is None:
		file_list = os.listdir('DataStorage/')
	else:
		file_list = os.listdir('DataStorage/' + subDir)
	file_list = [file for file in file_list if file.endswith(".csv")]

	return file_list

def getSummary(file_list, subDir=None):
	isError = False
	errorList = []
	f_GMSD = []
	f_Bitrate = []
	f_Stalling = []

	for filename in file_list:
		try:
			avg_GMSD, total_Bitrate, total_Stalling = readObservation(filename, subDir=subDir)
			f_GMSD.append(avg_GMSD)
			f_Bitrate.append(total_Bitrate)
			f_Stalling.append(total_Stalling)
			
		except Exception as err:
			print(f'{_log} Error occurs when processing: {filename}')
			errorList.append(filename)
			print(err)
			isError =True
	
	if isError:
		print(f'Exit caused by data error:')
		print(f'file names: {errorList}')
		exit(0)

	f_GMSD = list(map(float, f_GMSD))
	f_Bitrate = list(map(int, f_Bitrate))
	f_Stalling = list(map(int, f_Stalling))

	a_GMSD = round(sum(f_GMSD) / len(file_list), 7)
	a_bs = round(sum(f_Bitrate) / len(file_list), 0)
	a_se = round(sum(f_Stalling) / len(file_list), 0)

	print(f'Avg GMSD: {a_GMSD}')
	print(f'Total Bitrate Switch: {a_bs}')
	print(f'Total Stalling Event: {a_se}')

def main():
	print(f'Buffer Level: 10s')
	subDir = '221012_sep_set/cp12mfq2sbf10/'
	file_list = checkDataStorage(subDir)
	getSummary(file_list, subDir=subDir)

	print(f'\nBuffer Level: 15s')
	subDir = '221012_sep_set/cp12mfq2sbf15/'
	file_list = checkDataStorage(subDir)
	getSummary(file_list, subDir=subDir)

	print(f'\nBuffer Level: 30s')
	subDir = '221012_sep_set/cp12mfq2sbf30/'
	file_list = checkDataStorage(subDir)
	getSummary(file_list, subDir=subDir)

	print(f'\nBuffer Level: 60s')
	subDir = '221012_sep_set/cp12mfq2sbf60/'
	file_list = checkDataStorage(subDir)
	getSummary(file_list, subDir=subDir)

	print(f'\nBuffer Level: 90s')
	subDir = '221012_sep_set/cp12mfq2sbf90/'
	file_list = checkDataStorage(subDir)
	getSummary(file_list, subDir=subDir)

if __name__ == '__main__':
	main()