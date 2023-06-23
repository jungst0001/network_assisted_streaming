from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from calculateSSIM import getClientSSIM
import requests
import base64
from datetime import datetime

"""
install:
	pip3 install pybase64, scikit-image, opencv-python
"""

IP = '192.168.0.104'
PORT = 8889
RLSERVER_IP = '143.248.57.162'
EDGE_SERVER_IP = '143.248.57.171'
EDGE_SERVER_PORT = 22288

a = 0
b = 0

class SSIMHandler(BaseHTTPRequestHandler):
	_log = '[SSIMHandler]'

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
		global a
		global b
		self.send_response(200)
		self._send_cors_headers()
		# self.send_header('Content-type', 'application/json')
		self.end_headers()
		
		dataLength = int(self.headers["Content-Length"])
		data = self.rfile.read(dataLength).decode()

		ipdata = json.loads(data)
		imageData = ipdata['Snapshot']
		client_ip = imageData["IP"]

		# print(f'{self._log} {client_ip} image: {str(data)[0:20]}')
		if client_ip == '192.168.0.15':
			if a == 0:
				a = datetime.now()
			elif b == 0:
				b = datetime.now()
				print(f'incoming time is: {(b-a).total_seconds()}')
			else:
				a = b
				b = datetime.now()
				print(f'incoming time is: {(b-a).total_seconds()}')
		currentSSIM = self._getSSIM(client_ip, data)

		# print(f'{self._log} client_ip: {client_ip}, SSIM: {currentSSIM}')
		self._sendSSIMData(client_ip, currentSSIM)

		# body = f'{actions}'
		# self.wfile.write(body.encode())

	def _sendSSIMData(self, client_ip, SSIM):
		data = {}
		data['client_ip'] = client_ip
		data['SSIM'] = SSIM

		res = requests.post('http://' + EDGE_SERVER_IP + ':' + f'{EDGE_SERVER_PORT}',
			data=json.dumps(data))

	def _getSSIM(self, ip, data):
		# save Image data and calculate SSIM
		try:
			data = json.loads(data)
			imageData = data['Snapshot']

			# print(type(str(imageData)))
			# print(f'{self._log} {self.ip} image: {str(imageData)[0:20]}')

			# ip = imageData["IP"]
			frameNumber = imageData["FrameNumber"]
			extension = imageData["Type"]
			image = imageData["Image"]

			currentFrameNumber = frameNumber
			currentImageName = ip + "-" + str(frameNumber) + '.' + extension
			f = open('images/' + ip + "-" + str(frameNumber) + '.' + extension, 'wb')
			f.write(base64.b64decode(image))
			f.close()

			# print(f'{self._log} {ip} data: {str(imageData)[0:80]}')
			currentSSIM = getClientSSIM(currentImageName, currentFrameNumber)

			return currentSSIM
		except KeyError:
			return 0

if __name__ == "__main__":
	try:
		server = HTTPServer((IP, PORT), SSIMHandler)
		print(f'Started httpserver on port {PORT}')
		server.serve_forever()
	except KeyboardInterrupt:
		pass