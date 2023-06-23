from http.server import BaseHTTPRequestHandler, HTTPServer
import json

import videoDQN
# from VideoEnv import transformStatetoList
import VideoState

IP = '192.168.0.104'
PORT = 8888

RL_MODEL_INDEX=4
# OLD_MODEL model_06_28_03 is a default
# Model 'model_07_28_04' is a default
# The model name must be refered in videoDQN.py in every running
OLD_MODEL_NAME = ['model_06_28_01', 'model_06_28_02', 'model_06_28_03', 'model_06_28_04']
MODEL_NAME = ['model_07_28_01', 'model_07_28_02', 'model_07_28_03', 'model_07_28_04', 'model_07_28_05']

class RLServerHandler(BaseHTTPRequestHandler):
	_log = '[RLServerHandler]'

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

	def do_POST(self):
		self.send_response(200)
		self._send_cors_headers()
		self.send_header('Content-type', 'text/text')
		self.end_headers()
		
		dataLength = int(self.headers["Content-Length"])
		data = self.rfile.read(dataLength).decode()

		state = self._checkState(data)

		actions = videoDQN.run_saved_model(state, RL_MODEL_INDEX)

		print(f'{self._log} actions: {actions}')


		body = f'{actions}'
		self.wfile.write(body.encode())

	def _checkState(self, data):
		#          state is
		# server capacity
		# server throughput
		# server connected player
		#          each of players
		# bitrate
		# bufferLevel
		# SSIM
		# player_resolution
		# stalling
		# bitrate_switching

		state_json = json.loads(data)
		# print(f'{self._log} state: {state_json}')
		# state_list = transformStatetoList(state_json)

		state = state_json

		return state

if __name__ == "__main__":
	print(f'Target model: {MODEL_NAME[RL_MODEL_INDEX]}')

	try:
		server = HTTPServer((IP, PORT), RLServerHandler)
		print(f'Started httpserver on port {PORT}')
		server.serve_forever()
	except KeyboardInterrupt:
		pass