import paramiko 
import argparse
from scp import SCPClient, SCPException 

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

	def send_file(self, local_path, remote_path): 
		"""Send a single file to remote path""" 

		try: 
			with SCPClient(self.ssh_client.get_transport()) as scp: 
				scp.put(local_path, remote_path, preserve_times=True) 
		except SCPException: 
			raise SCPException.message 

	def get_file(self, remote_path, local_path): 
		"""Get a single file from remote path""" 

		try: 
			with SCPClient(self.ssh_client.get_transport()) as scp: 
				scp.get(remote_path, local_path) 
		except SCPException: 
			raise SCPException.message 

	def send_command(self, command): 
		"""Send a single command""" 
		stdin, stdout, stderr = self.ssh_client.exec_command(command) 
		return stdout.readlines()


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='Get a file from client2 and send it to all clients')
	parser.add_argument('-d', '--dir', dest='dir', type=str, help='set directory', default='/home/wins/')
	parser.add_argument('-f', '--fname', dest='fname', type=str, help='input file name', default=None)

	args = parser.parse_args()

	if args.fname is None:
		print('input file name')
		exit()

	mainDir = '/home/wins'
	if mainDir in args.dir:
		mainDir = args.dir
	else:
		mainDir = mainDir + args.dir

	client2 = "192.168.0.12"

	ipList = [
		"192.168.0.11",
		"192.168.0.13",
		"192.168.0.14",
		"192.168.0.15"
	]
	
	try:
		ssh_manager = SSHManager()
		ssh_manager.create_ssh_cleint(client2, 'wins', 'winslab')
		ssh_manager.get_file(mainDir + fname, fname)
		ssh_manager.close_ssh_client()
	except e:
		print(e)
		exit()
	
	for ip in ipList:
		ssh_manager = SSHManager()
		ssh_manager.create_ssh_cleint(ip, 'wins', 'winslab')
		ssh_manager.send_file(fname, mainDir)
		ssh_manager.close_ssh_client()
