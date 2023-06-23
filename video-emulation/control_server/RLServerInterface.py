from playerData import Player
# from playerHandler import PlayerHandler
import requests
import json
import cserverConfig

RLSERVER_IP = cserverConfig.RLSERVER_IP
RLSERVER_PORT = cserverConfig.RLSERVER_PORT

# capacity is MB per second
NETWORK_CAPACITY = cserverConfig.NETWORK_CAPCITY

IP_LIST = cserverConfig.IP_LIST

class RLServerInterface:
	def __init__ (self, CLIENT_NUM=5):
		self._log = '[RLServerInterface]'

		self.CLIENT_NUM = CLIENT_NUM

		self._currentReward = 0

	# send current state to RL Server via HTTP.
	# Return: list of actions (video quality)
	def getTestState1(self):
		state = {}
		server_state = [0 for i in range(3)]
		client_state = [{} for i in range(self.CLIENT_NUM)]
		state['server'] = server_state
		state['client'] = client_state

		# capacity is decided on the RL server
		capacity = NETWORK_CAPACITY
		throughput = 50000
		connected_player = 25

		server_state[0] = capacity
		server_state[1] = throughput
		server_state[2] = connected_player

		for i in range(self.CLIENT_NUM-25):
			client_state[i]['bitrate'] = 400
			client_state[i]['bufferLevel'] = 10.5
			client_state[i]['GMSD'] = 0.8222
			# client_state[i]['player_resolution'] = 720
			client_state[i]['stalling'] = 1 
			client_state[i]['bitrate_switching'] = 1
			client_state[i]['throughput'] = 2000

		for i in range(25, self.CLIENT_NUM):
			client_state[i]['bitrate'] = 0
			client_state[i]['bufferLevel'] = 0
			client_state[i]['GMSD'] = 0
			# client_state[i]['player_resolution'] = 720
			client_state[i]['stalling'] = 0
			client_state[i]['bitrate_switching'] = 0
			client_state[i]['throughput'] = 0

		return state

	def getTestState2(self):
		state = {}
		server_state = [0 for i in range(3)]
		client_state = [{} for i in range(self.CLIENT_NUM)]
		state['server'] = server_state
		state['client'] = client_state

		# capacity is decided on the RL server
		capacity = NETWORK_CAPACITY
		throughput = 20000
		connected_player = 50

		server_state[0] = capacity
		server_state[1] = throughput
		server_state[2] = connected_player

		for i in range(self.CLIENT_NUM):
			client_state[i]['bitrate'] = 400
			client_state[i]['bufferLevel'] = 10.5
			client_state[i]['GMSD'] = 0.8222
			# client_state[i]['player_resolution'] = 720
			client_state[i]['stalling'] = 1 
			client_state[i]['bitrate_switching'] = 1
			client_state[i]['throughput'] = 2000

		return state

	def progressData(self, players: list, serverMetrics: list):
		if len(serverMetrics) == 0:
			print(f'{self._log} server metrics does not exist')

			return None 

		# capacity = serverMetrics[-1][]
		
		state = {}
		server_state = [0 for i in range(3)]
		client_state = [{} for i in range(self.CLIENT_NUM)]
		state['server'] = server_state
		state['client'] = client_state

		# capacity is MB per second
		capacity = NETWORK_CAPACITY
		throughput = (serverMetrics[-1]['tx'] + serverMetrics[-1]['rx'])
		# throughput = serverMetrics[-1]['rx'] # only consider 'tx'
		connected_player = serverMetrics[-1]['connected']

		server_state[0] = capacity
		server_state[1] = throughput
		server_state[2] = len(players) # curr client num

		# for p in players:
		# 	resolution = p.getPlayerResolution()['height']

		# 	metrics = p.getMetrics()
		# 	if len(metrics) != 0:
		# 		bitrate = metrics[-1]['bitrate']
		# 		bufferLevel = metrics[-1]['bufferLevel']
		# 		SSIM = metrics[-1]['SSIM']
		# 		bitrate_switch = metrics[-1]['bitrateSwitch']
		# 		stalling = metrics[-1]['stalling']

		for i in range(self.CLIENT_NUM):
			client_state[i]['bitrate'] = 0
			client_state[i]['bufferLevel'] = 0
			client_state[i]['GMSD'] = 0
			# client_state[i]['player_resolution'] = 0
			client_state[i]['stalling'] = 0 
			client_state[i]['bitrate_switching'] = 0
			client_state[i]['throughput'] = 0

			for p in players:
				post_ip = p.ip.split('.')[-1]
				if i == int(post_ip) - 1:
					metrics = p.getMetrics()

					if len(metrics) != 0:
						client_state[i]['bitrate'] = metrics[-1]['bitrate']
						client_state[i]['bufferLevel'] = metrics[-1]['bufferLevel']
						# if float(metrics[-1]['GMSD']) < 0.70:
						# 	client_state[i]['GMSD'] = 0.70
						# else:
						# 	client_state[i]['GMSD'] = metrics[-1]['GMSD']
						client_state[i]['GMSD'] = metrics[-1]['GMSD']
						# client_state[i]['player_resolution'] = p.getPlayerResolution()['height']
						client_state[i]['stalling'] = metrics[-1]['stalling']
						client_state[i]['bitrate_switching'] = metrics[-1]['bitrateSwitch']
						if metrics[-1]['throughput'] == 0:
							for m in reversed(metrics):
								if float(m['throughput']) != 0:
									client_state[i]['throughput'] = m['throughput']
									break
						else:
							client_state[i]['throughput'] = metrics[-1]['throughput']

					break

		return state

	def sendCurrentState(self, currentState: dict):
		res = requests.post('http://' + RLSERVER_IP + ':' + f'{RLSERVER_PORT}',
			data=json.dumps(currentState))

		# print(f'{self._log} response: {res.json()}')
		# print(f'{self._log} response[0]: {res.json()[0]}')

		return res.json()

def main():
	rlInterface = RLServerInterface(CLIENT_NUM=50)
	state1 = rlInterface.getTestState1()

	actions1 = rlInterface.sendCurrentState(state1)

	print(actions1)

	state2 = rlInterface.getTestState2()

	actions2 = rlInterface.sendCurrentState(state2)

	print(actions2)

if __name__ == "__main__":
	main()
