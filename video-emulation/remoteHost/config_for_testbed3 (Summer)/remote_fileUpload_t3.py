import paramiko
import sys, argparse, os
from scp import SCPClient, SCPException 
import remote_clientConfig_t3 as remote_clientConfig

ClientIPList = remote_clientConfig.clientIPList


CLIENT_FILE_LIST = remote_clientConfig.FILE_LIST
CLIENT_LOCAL_DIR = remote_clientConfig.LOCAL_DIR
CLIENT_REMOTE_DIR = remote_clientConfig.REMOTE_DIR

_LOG = "[remote_fileUpload.py]"

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

	def create_ssh_client(self, hostname, username, password): 
		"""Create SSH client session to remote server""" 
		if self.ssh_client is None: 
			self.ssh_client = paramiko.SSHClient() 
			self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.ssh_client.connect(hostname, username=username, password=password) 

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
				scp.get(remote_path=remote_path, local_path=local_path) 
		except (SCPException, paramiko.ssh_exception) as e: 
			raise e.message 

	def send_command(self, command): 
		"""Send a single command""" 
		stdin, stdout, stderr = self.ssh_client.exec_command(command) 
		return stdout.readlines()


def updateClients(fname=None, clientIP=None, local_dir=None, remote_dir=None):
	ctfList = CLIENT_FILE_LIST

	if local_dir is None:
		# ctLocalDir = CLIENT_LOCAL_DIR
		ctLocalDir = remote_clientConfig.LOCAL_JS_DIR
	else:
		ctLocalDir = local_dir

	if remote_dir is None:
		# ctRemoteDir = CLIENT_REMOTE_DIR
		ctRemoteDir = remote_clientConfig.REMOTE_JS_DIR
	else:
		ctRemoteDir = remote_dir

	if fname is None:
		print(f'{_LOG} | all clients are updating')

		for cip in ClientIPList:
			ssh_manager = SSHManager()
			ssh_manager.create_ssh_client(cip, remote_clientConfig.client_user, remote_clientConfig.client_password)

			for ctfname in ctfList:
				ssh_manager.send_file(ctLocalDir + ctfname, ctRemoteDir)

			ssh_manager.close_ssh_client()
	else:
		if clientIP is None:
			print(f'{_LOG} | all clients are updating file {fname}')

			for cip in ClientIPList:
				ssh_manager = SSHManager()
				ssh_manager.create_ssh_client(cip, remote_clientConfig.client_user, remote_clientConfig.client_password)

				ssh_manager.send_file(ctLocalDir + fname, ctRemoteDir)

				ssh_manager.close_ssh_client()
		else:
			print(f'{_LOG} | a client {clientIP} is updating file {fname}')
			ssh_manager = SSHManager()
			ssh_manager.create_ssh_client(clientIP, remote_clientConfig.client_user, remote_clientConfig.client_password)

			ssh_manager.send_file(ctLocalDir + fname, ctRemoteDir)

			ssh_manager.close_ssh_client()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='easy scp to cserver, mserver, clients')
	parser.add_argument('-c', '--cli-update', dest='client_update', help='client.js update', action="store_true")

	args = parser.parse_args()

	if args.client_update:
		updateClients()

		exit()


	if args.specific is None:
		print('no specific IP')

		exit()