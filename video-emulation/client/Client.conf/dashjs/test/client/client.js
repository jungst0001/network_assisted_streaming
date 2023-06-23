// function httpPOST(data){
// 	console.log("start http POST");

// 	let url = "http://192.168.122.3:8888";
// 	let xhr = new XMLHttpRequest();
	
// 	xhr.onload = function () {
// 		if (xhr.readyState == 4 && xhr.status == 200) {
// 			console.log("print response data");
// 			console.log(xhr.responseText);
			
// 			quality = xhr.responseText; // quality is global variable

// 		}
// 	}
	
// 	xhr.open("POST", url); // false for synchrounous request
// 	xhr.setRequestHeader("Content-Type", "application/json");
// 	xhr.send(data);
// }

// function httpPOST_SSIM(data){
// 	let url = "http://143.248.57.162:8889";
// 	let xhr = new XMLHttpRequest();
	
// 	xhr.onload = function () {
// 		if (xhr.readyState == 4 && xhr.status == 200) {
// 			console.log("print response data");
// 			console.log(xhr.responseText);
			
// 			quality = xhr.responseText; // quality is global variable

// 		}
// 	}
	
// 	xhr.open("POST", url); // false for synchrounous request
// 	xhr.setRequestHeader("Content-Type", "application/json");
// 	xhr.send(data);
// }

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

	let dataURI = canvas.toDataURL('image/jpeg')

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

function postTimerHandler(player, currentRequestHead, ip, monitoringInterval, cserver_url) {
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
		// var throughput = player.getAverageThroughput('video');
		// var throughput = getThroughput('video', dashMetrics.getCurrentHttpRequest('video'));
		let throughput = getThroughput('video', dashMetrics.getHttpRequests('video'), currentRequestHead[0], monitoringInterval);
		currentRequestHead[0] = dashMetrics.getHttpRequests('video').length;
		let frameRate = adaptation.Representation_asArray.find(function (rep) {
			return rep.id === repSwitch.to
		}).frameRate;
		if (frameRate.includes('/')) {
			let split_str = frameRate.split("/");
			frameRate = Number(split_str[0]) / Number(split_str[1])
			frameRate = frameRate.toFixed(2)
		}

		console.log('throughput is:');
		console.log(throughput);


		let jsonData = JSON.stringify({
			"client_ip" : ip,
			"bufferLevel": bufferLevel,
			"bitrate": bitrate,
			"framerate": frameRate,
			"throughput": throughput,
			"index": currentRequestHead[1]
		});
		httpPOST(jsonData, cserver_url);
		currentRequestHead[1] += 1
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
