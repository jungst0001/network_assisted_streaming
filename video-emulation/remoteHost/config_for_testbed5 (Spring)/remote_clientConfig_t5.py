client_user = 'wins'
client_password = 'winslab'

clientIPList = [ 
	"192.168.122.44",
	"192.168.122.45"
	]

clientHostName = [ 
		"Client34",
		"Client35"
		]
		
OPTION_DIR = '/home/wins/jin/video_emulation/remoteHost/'
OPTION_FILENAME = 'remoteOption_t5.json'

LOCAL_DIR = '/home/wins/jin/video_emulation/remoteHost/ClientStorage/'
LOCAL_RUN_DIR = LOCAL_DIR
LOCAL_DASH_DIR = LOCAL_DIR + 'html/'
LOCAL_JS_DIR = LOCAL_DIR + 'js/'

REMOTE_DIR = '/home/wins/'
REMOTE_HTML_DIR = REMOTE_DIR + 'Client.conf/dashjs/emulator/'
REMOTE_JS_DIR = REMOTE_HTML_DIR + 'client/'

FILE_LIST = [
	'client.js'
	]

####################
"""
Client firefox setting

1.

type about:config in the firefox address bar
bypass the warning
change browser.sesstionstore.resume_from_crash to false
close firefox

open firefox nomally
repeat steps 2-4, but change the preference to true
restart firefox

2.
click three-bar option

click privacy tab

click autoplay setting

change block audio to allow audio and video

click save changes

3.
new tab forcly apply

https://support.mozilla.org/en-US/questions/1371648

"""