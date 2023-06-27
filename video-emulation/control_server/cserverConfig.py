# install guide

"""
pip3 install numpy scipy opencv-python
"""

##################

IP_LIST = ["192.168.0.11", "192.168.0.12", "192.168.0.13", "192.168.0.14", "192.168.0.15"] # Deprecated

# rlserver interface
NETWORK_CAPCITY = 300 * 1024 # 120 Mbit, 120 * 1024 Kbit
RLSERVER_IP = '192.168.122.1'
RLSERVER_PORT = 8889
MAX_CLIENT_NUM = 50

# server config

isEMULATION = True

cserver_user = 'wins'
cserver_password = 'wins2-champion'

cserver_IP = '127.0.0.1'
cserver_PORT = 8888
log_sendRLData = False
log_onlyMonitorQoE = False
log_getRLResult = False # False or True | False mean dynamic or other abr algorithm

# Video Comparison config
VIDEO_DIR = '/home/wins/Videos/'
VIDEO_NAME = 'enter-video-du8min'

BPS_400 = '_400_dashinit.mp4'
BPS_800 = '_800_dashinit.mp4'
BPS_1200 = '_1400_dashinit.mp4'
BPS_1600 = '_2000_dashinit.mp4'

# Video url
video_proxy_server = 'http://143.248.57.162/'
video_list = [
	'dash/BigBuckBunny/2sec_mod_BigBuckBunny.mpd'
]

# Cache Info
LOCAL_CACHE_DIR = 'cacheStorage/'
FIRSTURL_CACHE_KEY = 'http://video_server/'

# server DIR and file list
LOCAL_DIR = '/home/wins/jin/video_emulation/control_server/'
LOCAL_DATASET_DIR = LOCAL_DIR + 'DataStorage/'

REMOTE_DIR = '/home/wins/cserver/'
REMOTE_DATASET_DIR = REMOTE_DIR + 'DataStorage/'
FILE_LIST = [
	'cserverConfig.py',
	'playerData.py',
	'calculateGMSD.py',
	'server.py',
	'playerHandler.py',
	'serverData.py',
	'RLServerInterface.py',
	'sendData.py',
	'server_flask.py',
	'traffic.py',
	'../video_server/mserverConfig.py'
]
