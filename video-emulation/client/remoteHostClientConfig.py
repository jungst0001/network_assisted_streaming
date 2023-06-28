
player_ratio = None
resolution_ratio = None

RESOLUTION = [
	(1980, 1080),
	(1280, 720),
	(854, 480)
]

class RemoteHostData:
	def __init__(self):
		# SECURITY ISSUE PART
		self.remoteHost_User = 'wins'
		self.remoteHost_Password = 'wins2-champion'

		# SECURITY ISSUE PART
		self.remoteHost_IP = "143.248.55.176"
		self.remoteHost_PORT = 2224

		# SECURITY ISSUE PART
		self.mserverURL = "http://143.248.57.162:8088"
		self.cserverURL = "http://143.248.57.162:8888"
		self.rserverURL = "http://143.248.57.162:8889"

		self.remote_command_py_DIR = "/home/wins/jin/video_emulation/remoteHost/"
		self.remote_command_py_name = "remote_ClientHandler.py"
		self.remote_command_py = "python3 " + self.remote_command_py_DIR + self.remote_command_py_name

		self.clientIPList = [ 
			"192.168.122.21",
			"192.168.122.22",
			"192.168.122.23",
			"192.168.122.24",
			"192.168.122.25",
			"192.168.122.26",
			"192.168.122.27",
			"192.168.122.28",
			"192.168.122.29",
			"192.168.122.30"
			]

		self.clientHostName = [ 
			"Client11", 
			"Client12",
			"Client13",
			"Client14",
			"Client15",
			"Client16",
			"Client17",
			"Client18",
			"Client19",
			"Client20" 
			]

		self.OPTION_DIR = '/home/wins/jin/video_emulation/remoteHost/'
		self.OPTION_FILENAME = 'remoteOption.json'

		self.LOCAL_DIR = '/home/wins/jin/video_emulation/client/'
		self.LOCAL_RUN_DIR = self.LOCAL_DIR + 'Client.conf/'
		self.LOCAL_DASH_DIR = self.LOCAL_DIR + 'Client.conf/dashjs/emulator/'
		self.LOCAL_JS_DIR = self.LOCAL_DASH_DIR + 'client/'

		self.REMOTE_DIR = '/home/wins/jin/video_emulation/remoteHost/ClientStorage/'
		self.REMOTE_HTML_DIR = self.REMOTE_DIR + 'html/'
		self.REMOTE_JS_DIR = self.REMOTE_DIR + 'js/'

		self.FILE_LIST = [
			'client.js'
			]

		self.sshManager = None
		self.assignedPlayerNum = None
		self.runableClientNum = None

		self.assignedResolutionList = []

		self.shFileList = []
		self.fnameList = []
		self.htmlFileList = []

	def __str__(self):
		return str(f'{self.remoteHost_IP}:{self.remoteHost_PORT}')

def setRemoteHostData():
	# edit player ratio if remoteHostData num is changed
	global player_ratio
	global resolution_ratio
	player_ratio = (20, 20, 2, 4, 4) # (20, 20, 2, 4, 4) (0, 0, 1, 1, 1)
	resolution_ratio = (5, 15 ,5) # mean (FHD, HD, SD)

	rhdList = []

	rhd1 = RemoteHostData() # testbed-4 info (default)
	rhd2 = RemoteHostData() # testbed-1 info
	rhd3 = RemoteHostData() # Summer info
	rhd4 = RemoteHostData() # Sakura info
	rhd5 = RemoteHostData() # Spring info

	# testbed-1 info setting
	rhd2.remoteHost_IP = "143.248.55.17"
	rhd2.remoteHost_PORT = 2222
	rhd2.remote_command_py_name = "remote_ClientHandler_t1.py"
	rhd2.remote_command_py = "python3 " + rhd2.remote_command_py_DIR + rhd2.remote_command_py_name
	rhd2.clientIPList = [ 
		"192.168.122.31",
		"192.168.122.32",
		"192.168.122.33",
		"192.168.122.34",
		"192.168.122.35",
		"192.168.122.36",
		"192.168.122.37",
		"192.168.122.38",
		"192.168.122.39",
		"192.168.122.40"
		]
	rhd2.clientHostName = [ 
		"Client21", 
		"Client22",
		"Client23",
		"Client24",
		"Client25",
		"Client26",
		"Client27",
		"Client28",
		"Client29",
		"Client30" 
		]

	rhd2.OPTION_FILENAME = 'remoteOption_t1.json'

	# Summer info setting
	rhd3.remoteHost_IP = "143.248.57.171"
	rhd3.remoteHost_PORT = 22225
	rhd3.remoteHost_Password = 'winslab'
	rhd3.remote_command_py_name = "remote_ClientHandler_t3.py"
	rhd3.remote_command_py = "python3 " + rhd3.remote_command_py_DIR + rhd3.remote_command_py_name
	rhd3.clientIPList = [ 
		"192.168.122.41"
		]
	rhd3.clientHostName = [ 
		"Client31" 
		]

	rhd3.OPTION_FILENAME = 'remoteOption_t3.json'

	# Sakura info setting
	rhd4.remoteHost_IP = "143.248.57.171"
	rhd4.remoteHost_PORT = 22222
	rhd4.remoteHost_Password = 'winslab'
	rhd4.remote_command_py_name = "remote_ClientHandler_t4.py"
	rhd4.remote_command_py = "python3 " + rhd4.remote_command_py_DIR + rhd4.remote_command_py_name
	rhd4.clientIPList = [ 
		"192.168.122.42",
		"192.168.122.43"
		]
	rhd4.clientHostName = [ 
		"Client32",
		"Client33"
		]

	rhd4.OPTION_FILENAME = 'remoteOption_t4.json'

	# Spring info setting
	rhd5.remoteHost_IP = "143.248.57.171"
	rhd5.remoteHost_PORT = 22223
	rhd5.remoteHost_Password = 'winslab'
	rhd5.remote_command_py_name = "remote_ClientHandler_t5.py"
	rhd5.remote_command_py = "python3 " + rhd5.remote_command_py_DIR + rhd5.remote_command_py_name
	rhd5.clientIPList = [ 
		"192.168.122.44",
		"192.168.122.45"
		]
	rhd5.clientHostName = [ 
		"Client34",
		"Client35" 
		]

	rhd5.OPTION_FILENAME = 'remoteOption_t5.json'

	rhdList.append(rhd1)
	rhdList.append(rhd2)
	rhdList.append(rhd3)
	rhdList.append(rhd4)
	rhdList.append(rhd5)

	return rhdList

clientIPList = [ 
	"192.168.122.21",
	"192.168.122.22",
	"192.168.122.23",
	"192.168.122.24",
	"192.168.122.25",
	"192.168.122.26",
	"192.168.122.27",
	"192.168.122.28",
	"192.168.122.29",
	"192.168.122.30",
	"192.168.122.31",
	"192.168.122.32",
	"192.168.122.33",
	"192.168.122.34",
	"192.168.122.35",
	"192.168.122.36",
	"192.168.122.37",
	"192.168.122.38",
	"192.168.122.39",
	"192.168.122.40",
	"192.168.122.41",
	"192.168.122.42",
	"192.168.122.43",
	"192.168.122.44",
	"192.168.122.45"
	]

clientHostName = [ 
	"Client11", 
	"Client12",
	"Client13",
	"Client14",
	"Client15",
	"Client16",
	"Client17",
	"Client18",
	"Client19",
	"Client20", 
	"Client21", 
	"Client22",
	"Client23",
	"Client24",
	"Client25",
	"Client26",
	"Client27",
	"Client28",
	"Client29",
	"Client30",
	"Client31",
	"Client32",
	"Client33",
	"Client34",
	"Client35"   
	]