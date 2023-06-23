import requests

url = 'http://192.168.122.2:8088/dash/enter-video-du8min_MP4.mpd'
response = requests.get(url=url)

print(response.text)
