import os

_LOG = "player_blueprint.py"

LOG_LEVEL = "INFO" # "DEBUG"

class ScriptOption:
	def __init__(self):
		self.mserver_url = "http://192.168.122.2:8088"
		self.cserver_url = "http://192.168.122.3:8888"
		self.buffer_time = 15
		self.isAbr = "true"
		self.received_quality_interval = 1500
		self.send_monitoring_interval = 2500
		self.snapshot_interval = 5000
		self.strategy = "Dynamic"
		self.ip = "10.0.0.1"

class Script:
	def __init__(self):
		mserver_url = "http://192.168.122.2:8088"
		cserver_url = "http://192.168.122.3:8888"
		buffer_time = 15
		isAbr = "true"
		received_quality_interval = 1500
		send_monitoring_interval = 2500
		snapshot_interval = 5000
		strategy = "ABR_STRATEGY_DYNAMIC"
		ip = None

	def makeScript(self, 
		mserver_url="http://192.168.122.2:8088", 
		cserver_url = "http://192.168.122.3:8888",
		bf_time=15, is_Abr="true", 
		rq_interval=1500, 
		sm_interval=2500,
		ss_interval=5000,
		abr_strategy="Dynamic",
		ip=None):
		self.mserver_url = mserver_url
		self.cserver_url = cserver_url
		self.buffer_time = bf_time
		self.isAbr = is_Abr
		self.received_quality_interval = rq_interval
		self.send_monitoring_interval = sm_interval
		self.snapshot_interval = ss_interval
		self.ip = ip

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
		function init() {
"""

		blue_outro = """
			var eventPoller = setInterval(function () {
				var streamInfo = player.getActiveStream().getStreamInfo();
				var dashMetrics = player.getDashMetrics();
				var dashAdapter = player.getDashAdapter();
				var frameNumber;

				if (dashMetrics && streamInfo) {
					const periodIdx = streamInfo.index;
					var repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
					var bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
					var bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
					var adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo)
					
					var frameRate = adaptation.Representation_asArray.find(function (rep) {
						return rep.id === repSwitch.to
					}).frameRate;
					if (frameRate.includes('/')) {
						var split_str = frameRate.split("/");
						frameRate = Number(split_str[0]) / Number(split_str[1])
						frameRate = frameRate.toFixed(2)
					}
					var playhead = player.time();
					frameNumber = Math.ceil(playhead * frameRate);
					document.getElementById('bufferLevel').innerText = bufferLevel + " secs";
					document.getElementById('framerate').innerText = frameRate + " fps";
					document.getElementById('reportedBitrate').innerText = bitrate + " Kbps";
					document.getElementById('framenumber').innerText = frameNumber;
					document.getElementById('playhead').innerText = playhead;
				}
			}, 1000);

			// when player is closing (not handle force quit)
			window.addEventListener("beforeunload", function (e){
				var jsonData = JSON.stringify({
					"client_ip" : "%s",
					"status": "closed"
				});

				httpPOST(jsonData, "%s");
			});

			// var hearbeat =  setInterval(function () {
			//	 var jsonData = JSON.stringify({
			//		 "heartbeat":"hearbeat"
			//	 });

			//	 httpPOST(jsonData)
			// }, 500);


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
			width: 1280px;
			height: 720px;
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
		</div>
	</div>
	<script>
		document.addEventListener("DOMContentLoaded", function () {
			init();
		});
	</script>
<!--	 <a href="javascript:void(0);" onclick="downloadImg('/home/wins/snapshot/snapshot.jpeg')" class="main-btn__download">
		<span class="txt-hidden">Download image</span>
	</a> -->
</body>
</html>
"""%(self.ip, self.cserver_url)

		blue_init = """
			var video,
				player,
				url = "%s/dash/enter-video-du8min_MP4.mpd";

			video = document.querySelector("video");
			player = dashjs.MediaPlayer().create();
			player.initialize(video, url, true);

			player.updateSettings({
				streaming: {
					stableBufferTime: %d,
					richBufferThreshold: %d,
					bufferTimeAtTopQuality: 5,
					minBufferTimeFastSwitch: 5,
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

			let startupTime = new Date().getTime();
			let endTime;
"""%(self.mserver_url, self.buffer_time, self.buffer_time, self.strategy, self.isAbr)

		postTimer = """
			var currentReqeustHead = [0, 0];
			var postTimer = setInterval(function() {
				postTimerHandler(player, currentReqeustHead, "%s", %d, "%s");
			}, %d);
"""%(self.ip, self.send_monitoring_interval, self.cserver_url, self.send_monitoring_interval)

		event_playback_not_allowed = '''
			player.on(dashjs.MediaPlayer.events["PLAYBACK_NOT_ALLOWED"], function (){
				video.muted = true;
				// player.initialize(video, url, true);
			});
'''

		event_playback_ended = '''
			player.on(dashjs.MediaPlayer.events["PLAYBACK_ENDED"], function () {
				var jsonData = JSON.stringify({
					"client_ip" : "%s",
					"status": "closed"
				});

				httpPOST(jsonData, "%s");

				// clearInterval(eventPoller);
				// clearInterval(bitrateCalculator);

				// clearInterval(postTimer);
				// clearInterval(qualityTimer);
			});
'''%(self.ip, self.cserver_url)

		event_buffer_empty = '''
			player.on(dashjs.MediaPlayer.events["BUFFER_EMPTY"], function () {
				console.log('buffer stalled');
				var jsonStalled = JSON.stringify({
					"client_ip" : "%s",
					"BufferStalled":"true"
				});

				httpPOST(jsonStalled, "%s");
			});
'''%(self.ip, self.cserver_url)

		event_can_play1 = """
			var isFirst = 0;
			player.on(dashjs.MediaPlayer.events["CAN_PLAY"], function () {
				endTime = new Date().getTime();
				let startDelay = endTime - startupTime;
				isFirst += 1;

				if (isFirst < 2) {
					console.log('startup delay is %d', startDelay);
"""
		event_can_play2 = """
					let jsonStartupDelay = JSON.stringify({
						"client_ip" : "%s",
						"startupDelay": startDelay
					});

					httpPOST(jsonStartupDelay, "%s");
				}
			});
"""%(self.ip, self.cserver_url)

		# always last event position
		event_stream_initialized1 = """
			player.on(dashjs.MediaPlayer.events["STREAM_INITIALIZED"], function () {
				// player.setQualityFor('video', 1);
				// console.log(player.getQualityFor('video'));
				// httpGet()

				let video_width = getVideoWidth(video);
				let video_height = getVideoHeight(video);
				let jsonResolutionData = JSON.stringify({
					"client_ip" : "%s",
					"resolution": {
						"width": video_width,
						"height": video_height
					}
				});
				httpPOST(jsonResolutionData, "%s");
"""%(self.ip, self.cserver_url)

		event_stream_initialzed_qualityTimer = """
				var qualityTimer = setInterval(function() {
					let jsonData = JSON.stringify({
						"client_ip" : "%s",
						"type" : "quality"
					});

					httpPOST(jsonData, "%s")
					.then(res => res.json())
					.then(data => {
						console.log(data);
						player.setQualityFor('video', data.quality);
					});


					//let xhr = httpGet(jsonData)

					// xhr.addEventListener('load', function() {
					// 	let quality = xhr.responseText;
					// 	console.log("get quality is")
					// 	console.log(quality);
					// 	
					// 	if (quality >= 0) {
					// 		player.setQualityFor('video', quality);
					// 		// player.setAutoSwitchQualityFor('video', false);
					// 	}
					// });
					//console.log(quality);
					//player.setQualityFor('video', quality);
				}, %d);
"""%(self.ip, self.cserver_url, self.received_quality_interval)

		event_stream_initialzed_snapshotTimer = """
				snapshotTimer = setInterval(function() {
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
						if (frameRate.includes('/')) {
							let split_str = frameRate.split("/");
							frameRate = Number(split_str[0]) / Number(split_str[1]);
							frameRate = frameRate.toFixed(2);
						}
						let playhead = player.time();
						frameNumber = Math.ceil(playhead * frameRate);

						let dataURI = takeSnapshoot(video);

						let jsonData = JSON.stringify({
							"client_ip" : "%s",
							"bufferLevel": bufferLevel,
							"bitrate": bitrate,
							"framerate":frameRate,
							"Snapshot": {
								"FrameNumber" : frameNumber,
								"Type" : "jpeg",
								"Image" : dataURI
							}
						});
						httpPOST(jsonData, "%s");
					}
				}, %d);
"""%(self.ip, self.cserver_url, self.snapshot_interval)

		event_stream_initialzed_end = """
			});
"""

		old_event_stream_initialzed_postTimer = """
				var currentReqeustHead = 0;
				postTimer = setInterval(function() {
					var streamInfo = player.getActiveStream().getStreamInfo();
					var dashMetrics = player.getDashMetrics();
					var dashAdapter = player.getDashAdapter();
					// var currentConfig = player.getSettings();
					// var useDeadTimeLatency = currentConfig.streaming.abr.useDeadTimeLatency;

					if (dashMetrics && streamInfo) {
						const periodIdx = streamInfo.index;
						var repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
						var bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
						var bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
						var adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo);
						// var throughput = player.getAverageThroughput('video');
						// var throughput = getThroughput('video', dashMetrics.getCurrentHttpRequest('video'));
						var throughput = getThroughput('video', dashMetrics.getHttpRequests('video'), currentReqeustHead, %d);
						currentReqeustHead = dashMetrics.getHttpRequests('video').length;
						var frameRate = adaptation.Representation_asArray.find(function (rep) {
							return rep.id === repSwitch.to
						}).frameRate;
						if (frameRate.includes('/')) {
							var split_str = frameRate.split("/");
							frameRate = Number(split_str[0]) / Number(split_str[1]);
							frameRate = frameRate.toFixed(2);
						}

						// let requests = dashMetrics.getHttpRequests('video');
						// console.log('request num is :');
						// console.log(requests.length);

						console.log('throughput is:');
						console.log(throughput);

						var jsonData = JSON.stringify({
							"client_ip" : "%s",
							"bufferLevel": bufferLevel,
							"bitrate": bitrate,
							"framerate":frameRate,
							"throughput":throughput
						});
						httpPOST(jsonData, "%s");

						// var jsonImg = JSON.stringify({
						//	 "Snapshot": {
						//		 "IP" : "192.168.0.11",
						//		 "FrameNumber" : frameNumber,
						//		 "Type" : "png",
						//		 "Image" : dataURI
						//	 }
						// });
						// httpPOST_SSIM(jsonImg);
					}

					// var dataURI = takeSnapshoot(video);
					// console.log('send image data to server');
					// var jsonImageData = JSON.stringify({
					// "Snapshot": {
					//	 "FrameNumber" : frameNumber,
					//	 "Type" : "png",
					//	 "Image" : dataURI
					// }
					// });

					// httpPOST(jsonImageData);
				}, %d);
			});
"""%(self.send_monitoring_interval, self.ip, self.cserver_url, self.send_monitoring_interval)

		script = None
		script = blue_intro +\
			blue_init +\
			postTimer +\
			event_playback_not_allowed +\
			event_playback_ended +\
			event_can_play1 +\
			event_can_play2 +\
			event_stream_initialized1

			# event_buffer_empty +\

		if self.isAbr == "false":
			script = script + event_stream_initialzed_qualityTimer

		script = script +\
			event_stream_initialzed_snapshotTimer +\
			event_stream_initialzed_end +\
			blue_outro

		return script

def makeScript(option:ScriptOption):
	script = Script()
	return script.makeScript(option.mserver_url, 
		option.cserver_url,
		option.buffer_time, option.isAbr,
		option.received_quality_interval, 
		option.send_monitoring_interval, 
		option.snapshot_interval,
		option.strategy,
		option.ip)

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