import AutoDataGenerator
import paramiko
import sys, argparse, time
import subprocess


IP_LIST = [ "192.168.0.11",
		"192.168.0.12",
		"192.168.0.13",
		"192.168.0.14",
		"192.168.0.15"]

CLIENT_NAME = [ "Client01", 
		"Client02",
		"Client03",
		"Client04",
		"Client05" ]

Client01 = "192.168.0.11"
Client02 = "192.168.0.12"
Client03 = "192.168.0.13"
Client04 = "192.168.0.14"
Client05 = "192.168.0.15"

client_name = {'192.168.0.11' : 'Client01', '192.168.0.12' : 'Client02', '192.168.0.13' : 'Client03'}

user = "root"
password = "winslab"

command_restart = "reboot"

def log_string(str):
	log = '\033[95m' + str + '\033[0m'
	return log

def restartPlayerWithSSH(ip):
	if ip == Client01 or ip == Client02:
		subprocess.run(['virsh', 'reboot', client_name[ip]])
	else:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
		ssh.connect(ip, username=user, password=password)

		ssh.exec_command(command_restart)
	# lines = stdout.readlines()
	print(f'Client {ip} restart')

if __name__ == "__main__":
	# AutoDataGenerator.reboot_client()
	for ip in IP_LIST:
		restartPlayerWithSSH(ip)

		time.sleep(4)

	print(f'{log_string("Players reboot is done")}')