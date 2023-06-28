import os
import traceback

if __name__ == "__main__" or __name__ == "player_script_maker":
	import player_blueprint
	import clientConfig
else:
	from . import player_blueprint
	from . import clientConfig

def makeScript(f, scriptOption):
	script = buildScript(scriptOption)

	try:
		f.write(script)
	except Exception as err:
		print(f'player script file write function err: \n {traceback.format_exc()}')
		exit(0)
	# print("Making script is completed")

def buildScript(scriptOption):
	script = player_blueprint.makeScript(scriptOption)

	return script

def writePlayer(scriptOption, filename, player_category="firefox"):
	dirPath = clientConfig.LOCAL_DIR

	runPath = clientConfig.LOCAL_RUN_DIR
	dashPath = clientConfig.LOCAL_DASH_DIR

	sh_filename = filename + '.sh'
	html_filename = filename + '.html'

	f = open(runPath + sh_filename, 'w')
	makeRunningFile(f, dashPath, filename, player_category)
	f.close()

	f = open(dashPath + html_filename, 'w')
	makeScript(f, scriptOption)
	f.close()

	return sh_filename, html_filename

def makeRunningFile(f, dashPath, filename, player_category="firefox"):
	networkMonitor = None

	try:
		f.write("export DISPLAY=:0\n")
		# f.write("python3 {dashPath}{networkMonitor}.py &\n")
		# f.write(f'sudo -u wins {player_category} {clientConfig.REMOTE_HTML_DIR}{filename}.html &\n')
		f.write(f'{player_category} {clientConfig.REMOTE_HTML_DIR}{filename}.html &\n')
		f.write("sleep 1")
	except Exception as err:
		print(f'running script file write function err: \n {traceback.format_exc()}')
		exit(0)

def main():
	# Options parameter	
	dirPath = "/home/wins/jin/video_emulation/client/" 
	dashPath = dirPath + "Client.conf/dashjs/test/"
	filename = "test_live_streaming"

	scriptOption = player_blueprint.ScriptOption()
	scriptOption.mserver_url="http://127.0.0.1" 
	scriptOption.cserver_url="http://127.0.0.1:8888"
	scriptOption.buffer_time=4
	scriptOption.isAbr="true" 
	scriptOption.received_quality_interval=1500 
	scriptOption.strategy = "Dynamic"
	scriptOption.ip = "10.0.0.1"
	scriptOption.width = 854
	scriptOption.height = 480

	print(f'file path: {dashPath}')
	print(f'file name: {filename}')
	# f = open(dashPath + filename, 'w')
	# makeScript(f, scriptOption)
	# f.close()

	writePlayer(scriptOption, filename)

if __name__ == '__main__':
	main()