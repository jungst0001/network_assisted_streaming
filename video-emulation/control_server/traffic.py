import time, os, sys
import mserverConfig 
import paramiko, scp

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

def get_bytes_video_server(t):
	sshManager = SSHManager()
	sshManager.create_ssh_client(mserverConfig.mserver_IP,
		mserverConfig.mserver_user, mserverConfig.mserver_password)

	lines = sshManager.send_command('cat /sys/class/net/' + mserverConfig.iface + '/statistics/' + t + '_bytes')

	sshManager.close_ssh_client()

	return int(lines[0])

def get_bytes(t, iface='enp30s0'):
	with open('/sys/class/net/' + iface + '/statistics/' + t + '_bytes', 'r') as f:
		data = f.read()

		return int(data)

def get_speed_video_server():
	tx1 = get_bytes_video_server('tx')
	rx1 = get_bytes_video_server('rx')

	time.sleep(0.9)
	
	tx2 = get_bytes_video_server('tx')
	rx2 = get_bytes_video_server('rx')

	# tx_speed = round((tx2 - tx1)*8/1000.0, 4)
	# rx_speed = round((rx2 - rx1)*8/1000.0, 4)

	tx_speed = round((tx2 - tx1)/1024.0, 4)
	rx_speed = round((rx2 - rx1)/1024.0, 4)

	return tx_speed, rx_speed

def get_speed(iface='enp30s0'):
	tx1 = get_bytes('tx', iface)
	rx1 = get_bytes('rx', iface)

	time.sleep(0.9)
	
	tx2 = get_bytes('tx', iface)
	rx2 = get_bytes('rx', iface)

	# tx_speed = round((tx2 - tx1)*8/1000.0, 4)
	# rx_speed = round((rx2 - rx1)*8/1000.0, 4)

	tx_speed = round((tx2 - tx1)/1024.0, 4)
	rx_speed = round((rx2 - rx1)/1024.0, 4)

	return tx_speed, rx_speed


if __name__ == "__main__":
	print("traffic.py main")

	tx1 = get_bytes_video_server('tx')
	rx1 = get_bytes_video_server('rx')

	time.sleep(1)
	
	tx2 = get_bytes_video_server('tx')
	rx2 = get_bytes_video_server('rx')

	tx_speed = round((tx2 - tx1)/1000.0, 4)
	rx_speed = round((rx2 - rx1)/1000.0, 4)

	print(f'TX: {tx_speed}Kbps RX: {rx_speed}Kbps')
