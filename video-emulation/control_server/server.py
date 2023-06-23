from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
from playerData import getPlayer, Player
import json
from playerHandler import PlayerHandler
from bitrateCalculator import CAPACITY, BitrateCalculator
from threading import Timer
from serverData import ServerData
from calculateGMSD import calculateGMSD, getFrame 
import subprocess
import traceback
import cserverConfig

# IP_LIST = ["192.168.0.11", "192.168.0.12", "192.168.0.13", "192.168.0.14", "192.168.0.15"]

###############

EMULATION = cserverConfig.isEMULATION

###############

IP = cserverConfig.cserver_IP
PORT = cserverConfig.cserver_PORT
log_sendRLData = cserverConfig.log_sendRLData
log_onlyMonitorQoE = cserverConfig.log_onlyMonitorQoE
log_getRLResult = cserverConfig.log_getRLResult

###########################################################

playerHandler = PlayerHandler(sendRLData=log_sendRLData, getRLResult=log_getRLResult, 
	onlyMonitorQoE=log_onlyMonitorQoE)
bitrateCalculator = BitrateCalculator(playerHandler, CAPACITY)
serverData = ServerData(playerHandler)
playerHandler.setServerData(serverData)

class ServerTimer:
	def __init__(self, interval, function):
		self._log = '[ServerTimer]'

		self.interval = interval
		self.function = function
		self.timer = Timer(self.interval, self.function)

	def run(self):
		self.timer.start()

	def cancel(self):
		self.timer.cancel()

	def reset(self):
		self.timer.cancel()
		self.timer = Timer(self.interval, self.function)
		self.timer.start()

class ServerHandler(BaseHTTPRequestHandler):
	_log = '[ServerHandler]'
	ph = playerHandler
	bc = bitrateCalculator

	# request_queue_size = 1000
	# connection_limit = 500

	# Quit log message
	def log_message(self, format, *args):
		pass

	def _send_cors_headers(self):
		self.send_header("Access-Control-Allow-Origin", "*")
		self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		self.send_header("Access-Control-Allow-Headers", "Content-Type")
	
	def do_OPTIONS(self):
		self.send_response(204)
		self._send_cors_headers()
		self.end_headers()

	def _changeQuality(self):
		dataLength = int(self.headers["Content-Length"])
		data = self.rfile.read(dataLength).decode()
		quality = json.loads(data)['quality']
		
#		print(f'{self._log} current quality: {self.ph.getQuality()}')

		oldQuality = self.ph.getQuality()
		self.ph.setQuality(quality)
		
		print(f'{self._log} change quality: {oldQuality} -> {self.ph.getQuality()}')

	def do_POST(self):
		# print(f'{self._log} received POST message {self.client_address[0]}:{self.client_address[1]}')
		
		self.send_response(200)
		self._send_cors_headers()
		self.end_headers()

		client_ip = self.client_address[0]
		client_port = self.client_address[1]
		if client_ip == '127.0.0.1' or client_ip == '192.168.122.2':
			self._changeQuality()
			return
		elif client_ip == '192.168.122.3':
			dataLength = int(self.headers["Content-Length"])
			data = self.rfile.read(dataLength).decode()
			client_ip = json.loads(data)['client_ip']
			player = self.ph.getPlayer(client_ip)
			player.disconnectPlayer()

			print(f'{self._log} Manager ordered that the client {client_ip} is disconnected')
			return
		# elif client_ip == '143.248.57.162':
		# 	dataLength = int(self.headers["Content-Length"])
		# 	data = self.rfile.read(dataLength).decode()
		# 	player_ip = json.loads(data)['client_ip']
		# 	player = self.ph.getPlayer(player_ip)
		# 	GMSD = json.loads(data)['GMSD']
		# 	player.saveGMSD(GMSD)
			
		# 	return

		if EMULATION:
			try:
				dataLength = int(self.headers["Content-Length"])
				data = self.rfile.read(dataLength).decode()
				client_ip = json.loads(data)['client_ip']

				# print(f'{self._log} | data is arrived from {client_ip}')
				# print(f'{self._log} | data: {data[:60]}')
			except KeyError:
				return

		player = self.ph.getPlayer(client_ip, client_port)
		
		# print(f'{self._log} player num: {len(self.ph.getPlayers())}')
		# print(f'{self._log} player ip {client_ip}, player: {player.ip}')

		dataLength = int(self.headers["Content-Length"])
		try:
			if player is None:
				return
			# data = self.rfile.read(dataLength).decode()
			player.savePlayerData(data, self.ph.getServerInitTime())
		except ConnectionResetError:
			print(f'{self._log} the client {client_ip} is disconnected')
		except Exception:
			print(f'{self._log} when {client_ip} saving, error occurs')
			print(f'{self._log} metric save function err: \n {traceback.format_exc()}')
		
#		print(f'{self._log} received data is {data}')
#		print(f'{self._log} received data is saved')

# If player sends GET message to the edge server, return a result of RL server
	def do_GET(self):
#		print(f'{self._log} received GET message {self.client_address[0]}:{self.client_address[1]}')
		
		self.send_response(200)
		self._send_cors_headers()
		# self.send_header('Content-type', 'text/text')
		self.end_headers()
		
		client_ip = self.client_address[0]
		client_port = self.client_address[1]

		if EMULATION:
			try:
				if self.headers["Connection"] == "keep-alive":
					return

				dataLength = int(self.headers["Content-Length"])
				data = self.rfile.read(dataLength).decode()
				client_ip = json.loads(data)['client_ip']
			except KeyError:
				return

		player = self.ph.getPlayer(client_ip, client_port)
		if player is None:
			return
#		quality = self.ph.getQuality()
		# self.bc.optimizeBitrate()
		quality = player.getQualityIndex()

		# print(f'{self._log} RL quality is {client_ip}/{quality}')
		body = f'{quality}'

		self.wfile.write(body.encode())

if __name__ == "__main__":
	try:
		server = HTTPServer((IP, PORT), ServerHandler)
		server.request_queue_size = 1000000
		server.timeout = None
		print(f'Started httpserver on port {PORT}')
		print(f'Server Conf: sendRLData = {log_sendRLData}')
		print(f'Server Conf: onlyMonitorQoE = {log_onlyMonitorQoE}')
		print(f'Server Conf: getRLResult = {log_getRLResult}')
		server.serve_forever()
	except KeyboardInterrupt:
		pass
	# try:
	# 	server = socketserver.TCPServer((IP, PORT), ServerHandler)
	# 	print(f'Started httpserver on port {PORT}')
	# 	server.request_queue_size = 100
	# 	server.serve_forever()
	# except KeyboardInterrupt:
	# 	pass
	server.socket.close()
	print('Shutting down the web server')
	
	print('save player data')
	playerHandler.savePlayersData()
	print(f'file write error number per a client: {playerHandler.fileWriteErrorPerClient}')

	playerHandler.terminatePlayerProcess()
	print(f'terminate all player process')

	# subprocess.run(['rm', '/home/wins/server/images/*.png'])
	# subprocess.run(['rm', '/home/wins/server/images/server_images/*.png'])
	# print('clear server images and clients images')

	bitrateCalculator.destroyBitrateCalculator()
	playerHandler.destroyPlayerHandler()

	