import paramiko
import sys, argparse, os
from scp import SCPClient, SCPException 
from control_server import cserverConfig
from video_server import mserverConfig
from remoteHost import remote_clientConfig
from client import clientConfig
from client import remoteHostHandler

MServerIP = mserverConfig.mserver_IP
CServerIP = cserverConfig.cserver_IP

ClientIPList = clientConfig.clientIPList


CSERVER_FILE_LIST = cserverConfig.FILE_LIST
CSERVER_LOCAL_DIR = cserverConfig.LOCAL_DIR
CSERVER_REMOTE_DIR = cserverConfig.REMOTE_DIR

MSERVER_FILE_LIST = mserverConfig.FILE_LIST
MSERVER_LOCAL_DIR = mserverConfig.LOCAL_DIR
MSERVER_REMOTE_DIR = mserverConfig.REMOTE_DIR

CLIENT_FILE_LIST = clientConfig.FILE_LIST
CLIENT_LOCAL_DIR = clientConfig.LOCAL_DIR
CLIENT_REMOTE_DIR = clientConfig.REMOTE_DIR

_LOG = "[fileUpload.py]"

class SSHManager: 
	""" usage: 
	>>> import SSHManager 
	>>> ssh_manager = SSHManager() 
	>>> ssh_manager.create_ssh_client(hostname, username, password) 
	>>> ssh_manager.send_command("ls -al") 
	>>> ssh_manager.send_file("/path/to/local_path", "/path/to/remote_path") 
	>>> ssh_manager.get_file("/path/to/remote_path", "/path/to/local_path") ...
	>>> ssh_manager.close_ssh_client() 
	""" 
	def __init__(self): 
		self.ssh_client = None 

	def create_ssh_client(self, hostname, username, password, port=0): 
		"""Create SSH client session to remote server""" 
		if self.ssh_client is None: 
			self.ssh_client = paramiko.SSHClient() 
			self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

			if port == 0:
				self.ssh_client.connect(hostname, username=username, password=password) 
			else:
				self.ssh_client.connect(hostname, port=port, username=username, password=password)

		else: 
			print("SSH client session exist.") 

	def close_ssh_client(self): 
		"""Close SSH client session""" 
		self.ssh_client.close() 
		self.ssh_client = None

	def send_file(self, local_path, remote_path): 
		"""Send a single file to remote path""" 

		try: 
			with SCPClient(self.ssh_client.get_transport()) as scp: 
				scp.put(local_path, remote_path, preserve_times=True) 
		except (SCPException, paramiko.ssh_exception) as e: 
			raise e.message 

	def get_file(self, remote_path, local_path): 
		"""Get a single file from remote path""" 

		try: 
			with SCPClient(self.ssh_client.get_transport()) as scp: 
				scp.get(remote_path=remote_path, local_path=local_path, recursive=True) 
		except (SCPException, paramiko.ssh_exception) as e: 
			raise e.message 

	def send_command(self, command): 
		"""Send a single command""" 
		stdin, stdout, stderr = self.ssh_client.exec_command(command) 
		return stdout.readlines()

def updateCServer(fname=None):
	ssh_manager = SSHManager()
	ssh_manager.create_ssh_client(CServerIP, cserverConfig.cserver_user, cserverConfig.cserver_password)

	cfList = CSERVER_FILE_LIST
	csLocalDir = CSERVER_LOCAL_DIR
	csRemoteDir = CSERVER_REMOTE_DIR

	if fname is None:
		print(f'{_LOG} | cserver is updating all file')
		for cfname in cfList:
			cfname = csLocalDir + cfname
			ssh_manager.send_file(cfname, csRemoteDir)
	else:
		print(f'{_LOG} | cserver is updating file {fname}')
		ssh_manager.send_file(csLocalDir + fname, csRemoteDir)

	ssh_manager.close_ssh_client()

def downloadCServer(rule=None):
	ssh_manager = SSHManager()
	ssh_manager.create_ssh_client(CServerIP, cserverConfig.cserver_user, cserverConfig.cserver_password)

	print(f'{_LOG} | get all dataset from cserver')
	file_list = ssh_manager.send_command(f'ls {cserverConfig.REMOTE_DATASET_DIR}')

	for file in file_list:
		file = file.replace('\n', '')
		# f = open(cserverConfig.LOCAL_DATASET_DIR + file, 'w')
		# f.close()
		ssh_manager.get_file(cserverConfig.REMOTE_DATASET_DIR + file, cserverConfig.LOCAL_DATASET_DIR)

	ssh_manager.close_ssh_client()

def updateMServer(fname=None):
	ssh_manager = SSHManager()
	ssh_manager.create_ssh_client(MServerIP, mserverConfig.mserver_user, mserverConfig.mserver_password)

	mfList = MSERVER_FILE_LIST
	msLocalDir = MSERVER_LOCAL_DIR
	msRemoteDir = MSERVER_REMOTE_DIR

	if fname is None:
		for mfname in mfList:
			mfname = msLocalDir + mfname
			ssh_manager.send_file(mfname, msRemoteDir)
	else:
		ssh_manager.send_file(msLocalDir + fname, msRemoteDir)

	ssh_manager.close_ssh_client()

def updateClients(fname=None, clientIP=None, local_dir=None, remote_dir=None):
	ctfList = CLIENT_FILE_LIST

	if local_dir is None:
		# ctLocalDir = CLIENT_LOCAL_DIR
		ctLocalDir = clientConfig.LOCAL_JS_DIR
	else:
		ctLocalDir = local_dir

	if remote_dir is None:
		# ctRemoteDir = CLIENT_REMOTE_DIR
		ctRemoteDir = clientConfig.REMOTE_JS_DIR
	else:
		ctRemoteDir = remote_dir

	if fname is None:
		print(f'{_LOG} | all clients are updating')

		for cip in ClientIPList:
			ssh_manager = SSHManager()
			ssh_manager.create_ssh_client(cip, clientConfig.client_user, clientConfig.client_password)

			for ctfname in ctfList:
				ssh_manager.send_file(ctLocalDir + ctfname, ctRemoteDir)

			ssh_manager.close_ssh_client()
	else:
		if clientIP is None:
			print(f'{_LOG} | all clients are updating file {fname}')

			for cip in ClientIPList:
				ssh_manager = SSHManager()
				ssh_manager.create_ssh_client(cip, clientConfig.client_user, clientConfig.client_password)

				ssh_manager.send_file(ctLocalDir + fname, ctRemoteDir)

				ssh_manager.close_ssh_client()
		else:
			print(f'{_LOG} | a client {clientIP} is updating file {fname}')
			ssh_manager = SSHManager()
			ssh_manager.create_ssh_client(clientIP, clientConfig.client_user, clientConfig.client_password)

			ssh_manager.send_file(ctLocalDir + fname, ctRemoteDir)

			ssh_manager.close_ssh_client()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='easy scp to cserver, mserver, clients')
	parser.add_argument('-u', '--update', dest='update', help='all update cserver except mserver and clients', action="store_true")
	parser.add_argument('-f', '--fname', dest='fname', type=str, help='update a file to specific IP', default=None)
	parser.add_argument('-s', '--specific', dest='specific', type=str, help='update files to specific IP', default=None)
	parser.add_argument('-g', '--get', dest='get', help='download latest data from cserver', action="store_true")
	parser.add_argument('-c', '--cli-update', dest='client_update', help='client.js update', action="store_true")
	parser.add_argument('-r', '--remote-cli-update', dest='remote_update', help='remote client.js update', action="store_true")

	args = parser.parse_args()

	if args.client_update:
		updateClients()

		exit()

	if args.remote_update:
		remoteHostHandler = remoteHostHandler.RemoteHostHandler()

		for rhd in remoteHostHandler.rhdList:
			remoteHostHandler.updateRemoteJSFile(rhd)

		exit()

	if args.update:
		updateCServer()

		exit()

	if args.get:
		downloadCServer()

		exit()

	if args.specific is None:
		print('no specific IP')

		exit()
	else:
		if args.fname is None:
			if args.specific in CServerIP:
				updateCServer()
			elif args.specific in MServerIP:
				updateMServer()
			elif args.specific in ClientIPList:
				updateClients() # incomming any client ip makes all clients update. it is equal to all clients update
			else:
				print('incorrect IP')
		else:
			if args.specific in CServerIP:
				updateCServer(fname=args.fname)
			elif args.specific in MServerIP:
				updateMServer(fname=args.fname)
			elif args.specific in ClientIPList:
				updateClients(fname=args.fname) # incomming any client ip makes all clients update. only one file will be updated
			else:
				print('incorrect IP')

		exit()