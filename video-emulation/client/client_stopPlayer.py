import paramiko
import sys, argparse

user = "wins"
password = "winslab"

Client01 = "192.168.0.11"
Client02 = "192.168.0.12"
Client03 = "192.168.0.13"
Client04 = "192.168.0.14"
Client05 = "192.168.0.15"

command_ls = "ls"
#command_runPlayer = "wget dashjs/player.html/monitoring.html"
command_grep = "ps -ax | grep firefox "
command_stopPlayer = "kill "

command_snGrep = "ps -ax | grep sendNetwork "

def stopPlayerWithSSH(ip):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	ssh.connect(ip, username=user, password=password)

	stdin, stdout, stderr = ssh.exec_command(command_grep)
	lines = stdout.readlines()
	# print(f'Client {ip} pid Info: {lines}')
	pid = lines[0].split()[0]
	print(f'Client {ip} pid: {pid}')

	ssh.exec_command(command_stopPlayer + pid)

	stdin, stdout, stderr = ssh.exec_command(command_snGrep)
	lines = stdout.readlines()
	pid = lines[0].split()[0]
	print(f'Client {ip} pid: {pid}')

	ssh.exec_command(command_stopPlayer + pid)

parser = argparse.ArgumentParser(description='Running remote Player')
parser.add_argument('-s', '--specific', dest='specific', type=str, help = 'input player ip, ex) 192.168.0.11', default=None)
parser.add_argument('-n', '--number', dest='number', type=int, help = 'input to run player number', default=5)

args = parser.parse_args()


try:
	ipList = [
		Client01,
		Client02,
		Client03,
		Client04,
		Client05
	]

	if args.number != 0 and len(ipList) > args.number:
		for i in range(args.number):
#           print(f'run number')
			stopPlayerWithSSH(ipList[i])
	elif args.specific is not None:
		if args.specific in ipList:
#           print(f'run specific')
			stopPlayerWithSSH(args.specific)
		else:
			print(f'wrong specific')
	else:
		for ip in ipList:
#           print(f'default')
			stopPlayerWithSSH(ip)

except Exception as err:
	print(err)
