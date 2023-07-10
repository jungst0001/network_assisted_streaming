from flask import Flask, request, Response, make_response
from clientData import ClientData
import json
from ControlServerHandler import ControlServerHandler
from threading import Timer, Lock
from serverData import ServerData
import serverData as sd
from calculateGMSD import calculateGMSD, getFrame 
import subprocess
import traceback
import cserverConfig
from datetime import datetime
import psutil
import math
import time
import logging
log = logging.getLogger('werkzeug')
# log.setLevel(logging.ERROR)
log.disabled = True

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
	resp.headers.add('Access-Control-Allow-Methods', "GET, POST")
	
	return resp

def _changeQuality(data):
	quality = data['quality']

	oldQuality = playerHandler.getQuality()
	playerHandler.setQuality(quality)
	
	print(f'{_LOG} change quality: {oldQuality} -> {playerHandler.getQuality()}')

def do_POST():
	global playerLock

	client_ip = request.environ['REMOTE_ADDR']
	client_port = request.environ['REMOTE_PORT']

	try:
		data = request.get_json()
		client_ip = data['client_ip']
	except KeyError:
		print(f'{_LOG} client ip cannot be specific {data}')
		return

	isQuality = False

	try:
		if data['type'] == 'quality':
			isQuality = True
	except KeyError:
		pass

	player = None
	body = None
	try:
		playerLock.acquire()
		# print(f'{_LOG} client post reqeust received')
		player = playerHandler.getPlayer(client_ip, client_port)
	finally:
		playerLock.release()
	
	try:
		if player is None:
			print(f'{_LOG} player is none, request over')
			return
		elif isQuality:
			quality = player.getQualityIndex()

			# This is experimantal implementation
			# quality = 3
			###

			body = {}
			body['quality'] = quality

			return json.dumps(body)

		# start = time.time()
		# print(f'{_LOG} the client {client_ip} request comming!!')
		player.saveClientData(request.data.decode(), playerHandler.getServerInitTime())
		# print(f'{_LOG} the client {client_ip} request elapsed: {round((time.time()-start) * 1000)}ms')

		# log_getRLResult -> True: return cluster quality
		body = {}
		body['quality'] = -1

		if player.isMaster:
			body['master'] = 1
		else:
			body['master'] = 0
		if log_getRLResult:
			body['quality'] = player.getToBeQualityIndex()

		body = json.dumps(body)
	except ConnectionResetError:
		print(f'{_LOG} the client {client_ip} is disconnected')
	except Exception:
		print(f'{_LOG} when {client_ip} saving, error occurs')
		print(f'{_LOG} metric save function err: \n {traceback.format_exc()}')

	return body

def do_GET():
	global playerLock

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

@app.route('/disconnect', methods=['POST'])
def do_POST_disconnect():
	global playerLock

	client_ip = None 
	player = None

	resp = make_response('', 204)
	resp.headers.add("Access-Control-Allow-Origin", "*")

	try:
		data = json.loads(request.data.decode())
		client_ip = data['client_ip']
	except KeyError:
		print(f'{_LOG} client ip cannot be specific {data}')
		return resp

	try:
		playerLock.acquire()
		bool_player, player = playerHandler.isPlayer(client_ip)
	finally:
		playerLock.release()


	if bool_player is False:
		print(f'{_LOG} player is none, request over')
		return resp

	# print(f'signal client: {client_ip} to be disconnecting')
	player.setDisconnected()
	
	return resp

@app.route('/setquality', methods=['POST'])
def do_POST_setQuality():
	data = json.loads(request.data.decode())

	attribute = data['resolution']
	quality = data['quality']

	playerHandler.setClusterQuality(attribute, quality)

	resp = make_response('', 204)
	resp.headers.add("Access-Control-Allow-Origin", "*")
	return resp

@app.route('/livetime', methods=['GET'])
def do_GET_livetime():
	client_ip = request.environ['REMOTE_ADDR']
	height = request.args

	server, requestURI = playerHandler.getLiveStreamingInfo()
	if client_ip == '127.0.0.1':
		# For testing
		# print(f'{_LOG} Request URI: {requestURI}')
		server = 'http://127.0.0.1/'

	livetime = math.floor((datetime.now() - playerHandler.getServerInitTime()).total_seconds())

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
	print('save client data')
	serverData.cancelServerTimer()

	# if serverData.tsThread.is_alive():
	# 	serverData.isRunning = [False]

	playerHandler.savePlayersData()
	print(f'file write error number per a client: {playerHandler.fileWriteErrorPerClient}')

	print(f'file metric length minimum: {playerHandler.min_metric}')
	print(f'file metric length minimum ip: {playerHandler.min_ip}')
	print(f'file metric length maximum: {playerHandler.max_metric}')
	
	playerHandler.terminateClientThread()
	# print(f'terminate all player process')
	# playerHandler.destroyPlayerHandler()

	for proc in psutil.process_iter():
		if len(proc.cmdline()) == 2:
			if proc.cmdline()[1] in "server_flask.py":
				proc.kill()
	# playerHandler.tmp_waitPlayerToBeDisconn()