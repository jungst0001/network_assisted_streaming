from flask import Flask, request, Response, make_response
from playerData import getPlayer, Player
import json
from ControlServerHandler import ControlServerHandler
from threading import Timer, Lock
from serverData import ServerData
from calculateGMSD import calculateGMSD, getFrame 
import subprocess
import traceback
import cserverConfig
from datetime import datetime

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

playerLock = Lock()

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

playerHandler = ControlServerHandler(sendRLData=log_sendRLData, getRLResult=log_getRLResult, 
	onlyMonitorQoE=log_onlyMonitorQoE)
serverData = ServerData(playerHandler)
playerHandler.setServerData(serverData)

_LOG = '[server-flask]'

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


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST', 'OPTIONS'])
def index():
	if request.method == "POST":
		body = do_POST()

		if body is not None:
			# print(body)
			resp = make_response(body, 200)
		else:
			resp = make_response('', 204)
		resp.headers.add("Access-Control-Allow-Origin", "*")

		return resp

	elif request.method == "GET":
		body = do_GET()
		# print(body)

		if body is not None:
			resp = make_response(body, 200)
			resp.headers.add("Access-Control-Allow-Origin", "*")
			return resp
		else:
			resp = make_response('', 204)
			resp.headers.add("Access-Control-Allow-Origin", "*")
			return resp

	elif request.method == "OPTIONS":
		response = do_OPTIONS()
		return response

def do_OPTIONS():
	resp = make_response()
	resp.headers.add("Access-Control-Allow-Origin", "*")
	resp.headers.add('Access-Control-Allow-Headers', "*")
	resp.headers.add('Access-Control-Allow-Methods', "*")
	
	return resp

def _changeQuality(data):
	quality = data['quality']

	oldQuality = playerHandler.getQuality()
	playerHandler.setQuality(quality)
	
	print(f'{_LOG} change quality: {oldQuality} -> {playerHandler.getQuality()}')

def do_POST():
	client_ip = request.environ['REMOTE_ADDR']
	client_port = request.environ['REMOTE_PORT']
	if client_ip == '127.0.0.1' or client_ip == '192.168.122.2':
		# self._changeQuality(request.get_json())
		return
	elif client_ip == '192.168.122.3':
		client_ip = request.get_json()

		try:
			playerLock.acquire()
			player = playerHandler.getPlayer(client_ip)
		finally:
			playerLock.release()

		player.disconnectPlayer()

		print(f'{_LOG} Manager ordered that the client {client_ip} is disconnected')
		return

	if EMULATION:
		try:
			data = request.get_json()
			client_ip = data['client_ip']
			# print(data)
		except KeyError:
			return

	isQuality = False

	try:
		if data['type'] == 'quality':
			isQuality = True
	except KeyError:
		pass

	try:
		playerLock.acquire()
		player = playerHandler.getPlayer(client_ip, client_port)
	finally:
		playerLock.release()
	
	try:
		if player is None:
			return
		elif isQuality:
			quality = player.getQualityIndex()

			# This is experimantal implementation
			# quality = 3
			###

			body = {}
			body['quality'] = quality

			return json.dumps(body)

		player.saveClientData(request.data.decode(), playerHandler.getServerInitTime())
	except ConnectionResetError:
		print(f'{_LOG} the client {client_ip} is disconnected')
	except Exception:
		print(f'{_LOG} when {client_ip} saving, error occurs')
		print(f'{_LOG} metric save function err: \n {traceback.format_exc()}')

	return

def do_GET():
	client_ip = request.environ['REMOTE_ADDR']
	client_port = request.environ['REMOTE_PORT']

	try:
		playerLock.acquire()
		player = playerHandler.getPlayer(client_ip, client_port)
	finally:
		playerLock.release()
		
	if player is None:
		if client_ip == "192.168.122.1":
			pass
		else:
			return

	quality = player.getQualityIndex()

	body = f'{quality}'

	# print(body)

	return body

@app.route('/livetime', methods=['GET'])
def do_GET_livetime():
	client_ip = request.environ['REMOTE_ADDR']
	height = request.args
	

	print(f'{height}')

	server, requestURI = playerHandler.getLiveStreamingInfo()
	if client_ip == '127.0.0.1':
		# For testing
		print(f'{_LOG} Reqest URI: {requestURI}')
		server = 'http://127.0.0.1/'

	livetime = round((datetime.now() - playerHandler.getServerInitTime()).total_seconds())

	body = {}

	body['url'] = f'{server}{requestURI}#t={livetime}'
	# body['livetime'] = (datetime.now() - playerHandler.getServerInitTime()).total_seconds()
	body['quality'] = 2

	resp = make_response(json.dumps(body), 200)
	resp.headers.add("Access-Control-Allow-Origin", "*")
	# resp.headers.add('Access-Control-Allow-Headers', "*")
	# resp.headers.add('Access-Control-Allow-Methods', "*")

	return resp

if __name__ == "__main__":
	try:
		app.run(host=IP, port=PORT)
	except KeyboardInterrupt:
		pass

	print('Shutting down the web server')
	
	playerHandler.terminatePlayerThread()
	print(f'terminate all player process')
	# playerHandler.tmp_waitPlayerToBeDisconn()

	# print('save player data')
	# playerHandler.savePlayersData()
	# print(f'file write error number per a client: {playerHandler.fileWriteErrorPerClient}')

	# print(f'file metric length minimum: {playerHandler.min_metric}')
	# print(f'file metric length maximum: {playerHandler.max_metric}')

	playerHandler.destroyPlayerHandler()