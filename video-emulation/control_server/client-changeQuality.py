import requests, json, sys

url = 'http://192.168.0.2:8888'

quality = 0

if len(sys.argv) == 2:
	quality = sys.argv[1]

data = {'quality': quality}
response = requests.post(url=url, data=json.dumps(data))

print(response.text)
