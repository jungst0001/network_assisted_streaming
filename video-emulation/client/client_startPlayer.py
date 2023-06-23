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
command_runPlayer = "sh runPlayer.sh &"
command_runAbrPlayer = "sh runAbrPlayer.sh &"

# With ABR
command_runbfAbr10Player = "sh runBf10AbrPlayer.sh &"
command_runbfAbr15Player = "sh runBf15AbrPlayer.sh &"
command_runbfAbr30Player = "sh runBf30AbrPlayer.sh &"
command_runbfAbr60Player = "sh runBf60AbrPlayer.sh &"
command_runbfAbr90Player = "sh runBf90AbrPlayer.sh &"

# Without ABR
command_runbf10Player = "sh runBf10NotAbrPlayer.sh &"
command_runbf15Player = "sh runBf15NotAbrPlayer.sh &"
command_runbf30Player = "sh runBf30NotAbrPlayer.sh &"
command_runbf60Player = "sh runBf60NotAbrPlayer.sh &"
command_runbf90Player = "sh runBf90NotAbrPlayer.sh &"

command_grep = "ps -a | grep firefox"

def startPlayerWithSSH(ip, args):
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy)
	ssh.connect(ip, username=user, password=password)

	if args.abr is True:
		if args.bf == 10:
			ssh.exec_command(command_runbfAbr10Player)
		elif args.bf == 15:
			ssh.exec_command(command_runbfAbr15Player)
		elif args.bf == 30:
			ssh.exec_command(command_runbfAbr30Player)
		elif args.bf == 60:
			ssh.exec_command(command_runbfAbr60Player)
		elif args.bf == 90:
			ssh.exec_command(command_runbfAbr90Player)
		else:
			ssh.exec_command(command_runAbrPlayer)
	elif args.bf is not None:
		if args.bf == 10:
			ssh.exec_command(command_runbf10Player)
		elif args.bf == 15:
			ssh.exec_command(command_runbf15Player)
		elif args.bf == 30:
			ssh.exec_command(command_runbf30Player)
		elif args.bf == 60:
			ssh.exec_command(command_runbf60Player)
		elif args.bf == 90:
			ssh.exec_command(command_runbf90Player)
		else:
			print(f'bf level is wrong')
	else:
		ssh.exec_command(command_runPlayer)

	print(f'player {ip} is running')

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
