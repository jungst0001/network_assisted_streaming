import os

_LOG = "player_blueprint.py"

LOG_LEVEL = "INFO" # "DEBUG"

class ScriptOption:
	def __init__(self):
		self.mserver_url = "http://192.168.122.2:8088"
		self.cserver_url = "http://192.168.122.3:8888"
		self.buffer_time = 4
		self.isAbr = "true"
		self.received_quality_interval = 2000
		self.strategy = "Dynamic"
		self.ip = "10.0.0.1"
		self.width = 854
		self.height = 480

class Script:
	def __init__(self):
		mserver_url = "http://192.168.122.2:8088"
		cserver_url = "http://192.168.122.3:8888"
		buffer_time = 4
		isAbr = "true"
		received_quality_interval = 2000
		strategy = "ABR_STRATEGY_DYNAMIC"
		ip = None
		width = 854,
		height = 480

	def makeScript(self, 
		mserver_url="http://192.168.122.2:8088", 
		cserver_url = "http://192.168.122.3:8888",
		bf_time=4, 
		is_Abr="true", 
		received_quality_interval=2000,
		abr_strategy="Dynamic",
		ip=None,
		width = 854,
		height = 480):
		self.mserver_url = mserver_url
		self.cserver_url = cserver_url
		self.buffer_time = bf_time
		self.received_quality_interval = received_quality_interval
		self.isAbr = is_Abr
		self.ip = ip
		self.width = width
		self.height = height

		if abr_strategy == "BOLA":
			self.strategy = "abrBola"
			if LOG_LEVEL == "DEBUG":
				print("ABR Strategy is BOAL")
		elif abr_strategy == "L2A":
			self.strategy = "abrL2A"
			if LOG_LEVEL == "DEBUG":
				print("ABR Strategy is L2A")
		elif abr_strategy == "LoLP":
			self.strategy = "abrLoLP"
			if LOG_LEVEL == "DEBUG":
				print("ABR Strategy is LoLP")
		elif abr_strategy == "Throughput":
			self.strategy = "abrThroughput"
			if LOG_LEVEL == "DEBUG":
				print("ABR Strategy is Throughput")
		else:
			self.strategy = "abrDynamic"
			if LOG_LEVEL == "DEBUG":
				print("ABR Strategy is Default")

		blue_intro = """<html lang="en">
<head>
	<meta charset="utf-8"/>
	<title>Monitoring stream</title>
	<script src="client/client.js"></script>
	<script src="../dash.js/contrib/akamai/controlbar/ControlBar.js"></script>
	<script src="../dash.js/dist/dash.all.debug.js"></script>
	<script src="../dash.js/dist/dash.mss.debug.js"></script>
	<script class="code">
"""
		blue_outro = """
			var eventPoller = setInterval(function () {
				let streamInfo = player.getActiveStream().getStreamInfo();
				let dashMetrics = player.getDashMetrics();
				let dashAdapter = player.getDashAdapter();
				let frameNumber;

				if (dashMetrics && streamInfo) {
					const periodIdx = streamInfo.index;
					let repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
					let bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
					let bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
					let adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo)
					
					let frameRate = adaptation.Representation_asArray.find(function (rep) {
						return rep.id === repSwitch.to
					}).frameRate;
					if (isNaN(frameRate) && frameRate.includes('/')) {
						let split_str = frameRate.split("/");
						frameRate = Number(split_str[0]) / Number(split_str[1])
						frameRate = frameRate.toFixed(2)
					}
					let playhead = player.time();
					frameNumber = Math.ceil(playhead * frameRate);
					let d = new Date();
					videoDelay = Math.round((d.getTime() / 1000) + playback_startTime - Number(player.timeAsUTC()));
					document.getElementById('bufferLevel').innerText = bufferLevel + " secs";
					document.getElementById('framerate').innerText = frameRate + " fps";
					document.getElementById('reportedBitrate').innerText = bitrate + " Kbps";
					document.getElementById('framenumber').innerText = frameNumber;
					document.getElementById('playhead').innerText = playhead;
					document.getElementById('videoDelay').innerText = videoDelay;
				}

				if (videoDelay >= 6) {
					console.log('video delay upper 6sec');
					let seekTime = Math.round(player.time() + videoDelay);
					player.seek(seekTime);
					chunk_skip_event = 1;
				}
			}, 1000);

			// when player is closing (not handle force quit)
			window.addEventListener("beforeunload", function (e){
				var jsonData = JSON.stringify({
					"client_ip" : client_ip,
					"status": "closed"
				});

				httpPOST(jsonData, cserver_url);
			});

			if (video.webkitVideoDecodedByteCount !== undefined) {
				var lastDecodedByteCount = 0;
				const bitrateInterval = 1;
				var bitrateCalculator = setInterval(function () {
					var calculatedBitrate = (((video.webkitVideoDecodedByteCount - lastDecodedByteCount) / 1000) * 8) / bitrateInterval;
					document.getElementById('calculatedBitrate').innerText = Math.round(calculatedBitrate) + " Kbps";
					lastDecodedByteCount = video.webkitVideoDecodedByteCount;
				}, bitrateInterval * 1000);
			} else {
				document.getElementById('chrome-only').style.display = "none";
			}
		}
	</script>
	<style>
		video {
			width: %dpx;
			height: %dpx;
		}

		#container {
			display: inline-block;
		}

		#container > div {
			display: inline-block;
			float: left;
			margin-right: 10px;
		}

	</style>
</head>
<body>
	<div id="container">
		<div class="video-container">
			<video data-dashjs-player autoplay controls="true">
			</video>
		</div>
		<div>
			<strong>Reported bitrate:</strong>
			<span id="reportedBitrate"></span>
			<br/>
			<strong>Buffer level:</strong>
			<span id="bufferLevel"></span>
			<div id="chrome-only">
				<strong>Calculated bitrate:</strong>
				<span id="calculatedBitrate"></span>
			</div>
			<br/>
			<strong>Framerate:</strong>
			<span id="framerate"></span>
			<br/>
			<strong>Frame number:</strong>
			<span id="framenumber"></span>
			<br/>
			<strong>Playhead:</strong>
			<span id="playhead"></span>
			<br/>
			<strong>Video Delay:</strong>
			<span id="videoDelay"></span>
		</div>
	</div>
	<script>
		document.addEventListener("DOMContentLoaded", function () {
			init(video_play);
		});
	</script>
</body>
</html>
"""%(self.width, self.height)

		blue_init = """\tasync function init(callback) {
			let video = document.querySelector("video");
			const initResponse = await httpInitGET("%s/livetime", video);

			callback(initResponse);
		}

		function video_play(initResponse) {
			var video, player, url;
			
			var client_ip = "%s";
			var cserver_url = "%s";
			video = document.querySelector("video");
			player = dashjs.MediaPlayer().create();

			console.log(initResponse);
			url = initResponse.url;
			const initQuality = initResponse.quality; 

			player.initialize(video, url, true);

			player.updateSettings({
				streaming: {
					stableBufferTime: %d,
					fastSwitchEnabled: true,
					abr: {
						ABRStrategy: "%s",
						//useDefaultABRRules: true
						autoSwitchBitrate: {video: %s}
					},
					debug: {
						logLevel: dashjs.Debug.LOG_LEVEL_INFO
					}
				}
			});

			var playback_startTime;
			var playback_startTimeOnOff = true;
			var isStalling = false;
			var eventInterval = new Date();
			var chunk_skip_event = 0;

			player.on(dashjs.MediaPlayer.events["PLAYBACK_STARTED"], function (){
				if(playback_startTimeOnOff == true) {
					playback_startTime = player.time();
					playback_startTimeOnOff = false;
				}
			});

			player.on(dashjs.MediaPlayer.events["FRAGMENT_LOADING_COMPLETED"], function (e) {
				postHandler(player, video, e, client_ip, cserver_url, isStalling, eventInterval, chunk_skip_event);
				isStalling = false;
				eventInterval = new Date();
				chunk_skip_event = 0;
			});

			player.on(dashjs.MediaPlayer.events["PLAYBACK_NOT_ALLOWED"], function (){
				video.muted = true;
			});

			player.on(dashjs.MediaPlayer.events["BUFFER_EMPTY"], function () {
				isStalling = true;
				console.log('buffer stalled');
			});

			player.on(dashjs.MediaPlayer.events["STREAM_INITIALIZED"], function () {
				player.setQualityFor('video', initQuality);

				let video_width = getVideoWidth(video);
				let video_height = getVideoHeight(video);
				let jsonResolutionData = JSON.stringify({
					"client_ip" : client_ip,
					"resolution": {
						"width": video_width,
						"height": video_height
					}
				});

				httpPOST(jsonResolutionData, cserver_url);
			});

			window.addEventListener("beforeunload", function (e){
				var jsonData = JSON.stringify({
					"client_ip" : client_ip,
					"status": "closed"
				});

				httpPOST(jsonData, cserver_url);
			});

			player.on(dashjs.MediaPlayer.events["PLAYBACK_ENDED"], function () {
				var jsonData = JSON.stringify({
					"client_ip" : client_ip,
					"status": "closed"
				});

				httpPOST(jsonData, cserver_url);
			});
"""%(self.cserver_url, self.ip, self.cserver_url, self.buffer_time, self.strategy, self.isAbr)

		event_qualityTimer = """
			var qualityTimer = setInterval(function() {
				let jsonData = JSON.stringify({
					"client_ip" : client_ip,
					"type" : "quality"
				});

				httpPOST(jsonData, cserver_url)
				.then(res => res.json())
				.then(data => {
					console.log(data);
					player.setQualityFor('video', data.quality);
				});

			}, %d);
"""%(self.received_quality_interval)

		script = None
		script = blue_intro +\
			blue_init

		# if self.isAbr == "false":
		# 	script = script + event_qualityTimer

		script = script + blue_outro

		return script

def makeScript(option:ScriptOption):
	script = Script()
	return script.makeScript(option.mserver_url, 
		option.cserver_url,
		option.buffer_time, 
		option.isAbr,
		option.received_quality_interval, 
		option.strategy,
		option.ip,
		option.width,
		option.height)

def main():
	# print(blue_intro)
	# print(blue_init)
	# print(event_buffer_empty)
	# print(event_can_play)
	# print(event_playback_not_allowed)
	# print(event_stream_initalized)
	# print(blue_outro)
	scriptOption = ScriptOption()
	print(scriptOption.mserver_url)
	script = makeScript(scriptOption)

	print(script)

if __name__ == "__main__":
	main()