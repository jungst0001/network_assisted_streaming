client_user = 'wins'
client_password = 'winslab'

clientIPList = [ 
	"192.168.122.11",
	"192.168.122.12",
	"192.168.122.13",
	"192.168.122.14",
	"192.168.122.15",
	"192.168.122.16",
	"192.168.122.17",
	"192.168.122.18",
	"192.168.122.19",
	"192.168.122.20"
	]

clientHostName = [ 
	"Client01", 
		"Client02",
		"Client03",
		"Client04",
		"Client05",
		"Client06",
		"Client07",
		"Client08",
		"Client09",
		"Client10" 
		]

LOCAL_DIR = '/home/wins/jin/video_emulation/client/'
LOCAL_RUN_DIR = LOCAL_DIR + 'Client.conf/'
LOCAL_DASH_DIR = LOCAL_DIR + 'Client.conf/dashjs/emulator/'
LOCAL_JS_DIR = LOCAL_DASH_DIR + 'client/'

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

about:config
browser.link.open_newwindow.override.external
2 = open external links in a new window

"""