import paramiko, sys
import argparse

user = "wins"
password = "winslab"

Client01 = "192.168.0.11"
Client02 = "192.168.0.12"
Client03 = "192.168.0.13"
Client04 = "192.168.0.14"
Client05 = "192.168.0.15"

command_ls = "ls"
#command_runPlayer = "wget dashjs/player.html/monitoring.html"
# Without Img
command_withoutImg = "sh runWithoutImg.sh &"

command_grep = "ps -a | grep firefox"

def startPlayerWithSSH(ip, args):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	ssh.connect(ip, username=user, password=password)

	ssh.exec_command(command_withoutImg)

	print(f'player {ip} is running [WithoutImg version]')

##########################################

parser = argparse.ArgumentParser(description='Running remote Player')
parser.add_argument('-s', '--specific', dest='specific', type=str, help = 'input player ip, ex) 192.168.0.11', default=None)
parser.add_argument('-n', '--number', dest='number', type=int, help = 'input to run player number', default=5)
parser.add_argument('-A', '--Abr', dest='abr',type=bool, help = 'run client with abr streaming', default = False)
parser.add_argument('-B', '--Bf', dest='bf',type=int, help = 'run client with buffer level 15 and abr streaming', default = False)

args = parser.parse_args()

#if len(sys.argv) == 2:
#	ipRange = int(sys.argv[1])
#else:
#	ipRange = 0

try:
	ipList = [
		Client01, 
		Client02, 
		Client03, 
		Client04, 
		Client05
	]

#	startPlayerWithSSH(ipList[3])
	if args.number != 0 and len(ipList) > args.number:
		for i in range(args.number):
#			print(f'run number')
			startPlayerWithSSH(ipList[i], args)
	elif args.specific is not None:
		if args.specific in ipList:
#			print(f'run specific')
			startPlayerWithSSH(args.specific, args)
		else:
			print(f'wrong specific')
	else:
		for ip in ipList:
#			print(f'default')
			startPlayerWithSSH(ip, args)
	
except Exception as err:
	print(err)
