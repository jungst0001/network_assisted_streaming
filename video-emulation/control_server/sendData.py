import paramiko 
from scp import SCPClient, SCPException 

class SSHManager: 
	""" 
	usage: 
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

	def create_ssh_client(self, hostname, username, password, port=22): 
		"""Create SSH client session to remote server""" 
		if self.ssh_client is None: 
			self.ssh_client = paramiko.SSHClient() 
			self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) 
			self.ssh_client.connect(hostname, username=username, password=password, port=port) 
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


def sendFileToRLServer(filename):
	localDir = "DataStorage/"
	remoteDir = "/home/wins/jin/VideoDQN/DataStorage/"
	
	ssh_manager = SSHManager() 
	ssh_manager.create_ssh_client("143.248.57.162", "wins", "wins2-champion", 2222) 
	ssh_manager.send_file(localDir + filename, remoteDir)
	ssh_manager.close_ssh_client()

def main():
	ssh_manager = SSHManager() 
	ssh_manager.create_ssh_client("143.248.57.162", "wins", "wins2-champion", 2222) 
	stdout = ssh_manager.send_command("ls")
	print(stdout)
#	ssh_manager.create_ssh_client("hostname", "username", "password") # 세션생성 
#	ssh_manager.send_file("local_path", "remote_path") # 파일전송 
#	ssh_manager.get_file('remote_path', 'local_path') # 파일다운로드 
	ssh_manager.close_ssh_client() # 세션종료

if __name__ == "__main__":
	main()
