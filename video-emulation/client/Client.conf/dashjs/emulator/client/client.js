async function httpInitGET(url, video){
	console.log("start InitGet");
	
	const baseurl = url;
	const screen_width = getVideoWidth(video);
	const screen_height = getVideoHeight(video);

	const params = {
		"width" : screen_width,
		"height" : screen_height
	};

	const queryParams = new URLSearchParams(params);
	let queryString = queryParams.toString();

	const requrl = url + '?' + queryString;

	console.log(requrl);

	const response = await fetch(requrl);

	return response.json();
}

async function httpPOST(data, url){
	let response = await fetch(url, {
		method: "POST",
		body: data,
		headers: {
			"Content-Type": "application/json"
		}
	});

	return response;
}

function arrayBufferToBase64( buffer ) {
    let binary = '';
    let bytes = new Uint8Array( buffer );
    let len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode( bytes[ i ] );
    }
    return window.btoa( binary );
}

function getVideoWidth(video) {
	let video_width = document.defaultView.getComputedStyle(video).getPropertyValue("width");
	video_width = Number(video_width.slice(0, video_width.length - 2));

	return video_width;
}

function getVideoHeight(video) {
	let video_height = document.defaultView.getComputedStyle(video).getPropertyValue("height");
	video_height = Number(video_height.slice(0, video_height.length - 2));
	return video_height;
}

function takeSnapshoot(video) {
	let canvas = document.createElement('canvas');
	let video_width = getVideoWidth(video);
	let video_height = getVideoHeight(video);
	canvas.width = video_width;
	canvas.height = video_height;

	let ctx = canvas.getContext('2d');
	ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

	let dataURI = canvas.toDataURL('image/jpeg', 0.5).substring(22);

	// let dataURI = canvas.toDataURL('image/jpeg').substring(21); // 'image/png' or 'image/jpeg'

	return dataURI;
}

function getThroughput(type, httpRequests, currentRequestHead, metricsInterval) {
	// const latencyTimeInMilliseconds = (httpRequest.tresponse.getTime() - httpRequest.trequest.getTime()) || 1;
    // const downloadTimeInMilliseconds = (httpRequest._tfinish.getTime() - httpRequest.tresponse.getTime()) || 1; //Make sure never 0 we divide by this value. Avoid infinity!
    let downloadBytes = 0;
    let throughput = 0;
    let throughputMeasureTime = metricsInterval;

    for(i = currentRequestHead; i<httpRequests.length; i++) {
    	httpRequest = httpRequests[i];
    	downloadBytes += httpRequest.trace.reduce((a, b) => a + b.b[0], 0);
    }

    if (throughputMeasureTime !== 0) {
        throughput = Math.round((8 * downloadBytes) / throughputMeasureTime); // bits/ms = kbits/s
        // throughput = downloadBytes / throughputMeasureTime;
    }

    // console.log('downloadBytes: %d bytes', downloadBytes);
    // console.log('throughputMeasureTime: %d ms', throughputMeasureTime);
    console.log('calculated bandwidth: %d Kbits/s', throughput);

    return throughput;
}

function postHandler(player, video, event, ip, cserver_url, isStalling, eventInterval, 
	chunk_skip_event, server_latency, isMaster) {
	let streamInfo = player.getActiveStream().getStreamInfo();
	let dashMetrics = player.getDashMetrics();
	let dashAdapter = player.getDashAdapter();
	// var currentConfig = player.getSettings();
	// var useDeadTimeLatency = currentConfig.streaming.abr.useDeadTimeLatency;

	if (dashMetrics && streamInfo) {
		const periodIdx = streamInfo.index;
		let repSwitch = dashMetrics.getCurrentRepresentationSwitch('video', true);
		let bufferLevel = dashMetrics.getCurrentBufferLevel('video', true);
		let bitrate = repSwitch ? Math.round(dashAdapter.getBandwidthForRepresentation(repSwitch.to, periodIdx) / 1000) : NaN;
		let adaptation = dashAdapter.getAdaptationForType(periodIdx, 'video', streamInfo);
		
		let frameRate = adaptation.Representation_asArray.find(function (rep) {
			return rep.id === repSwitch.to
		}).frameRate;
		if (isNaN(frameRate) && frameRate.includes('/')) {
			let split_str = frameRate.split("/");
			frameRate = Number(split_str[0]) / Number(split_str[1])
			frameRate = frameRate.toFixed(2)
		}
		let playhead = player.time();
		let frameNumber = Math.ceil(playhead * frameRate);
		let dataURI = 0;

		if (event.request.url.includes('init')){
			console.log('get init.mp4');
		} else {
			if (isMaster[0] == true) {
				dataURI = takeSnapshoot(video);
			}
		}

		if (isStalling) {
			isStalling = "True";
		} else {
			isStalling = "False";
		}

		let d = new Date();
		let eInterval = d.getTime() - eventInterval.getTime();
		let currentQuality = player.getQualityFor('video');

		let jsonData = JSON.stringify({
			"client_ip" : ip,
			"bufferLevel": bufferLevel,
			"bitrate": bitrate,
			"framerate": frameRate,
			"playhead": playhead,
			"request_url": event.request.url,
			"request_url_quality": event.request.quality,
			"request_url_startTime": event.request.startTime,
			"response_length": event.response.byteLength,
			"stalling": isStalling,
			"requestInterval": eInterval,
			"currentQuality": currentQuality,
			"chunk_skip": chunk_skip_event,
			"latency" : server_latency,
			"captured": {
				"frameNumber": frameNumber,
				"type": "jpeg",
				"image": dataURI
			}
		});
		
		httpPOST(jsonData, cserver_url)
			.then(res => res.json())
			.then(res => {
			if (res.master != 0) {
				isMaster[0] = true
			}

			if (res.quality >= 0) {
				player.setQualityFor('video', res.quality);
			}
		});
	}
}

// function getNetworkStatistics(category) {
// 	const iface = 'ens3'
// 	const execSync = require('child_process').execSync;

// 	var command = 'cat /sys/class/net/' + iface + '/statistics/' + category + '_bytes';

// 	const output = execSync(command, { encoding: 'utf-8' });
// 	console.log('network speed of %s is: %s', category, output);

// 	return output
// }
