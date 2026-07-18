import urllib.request, json
req = urllib.request.Request('https://api.github.com/repos/JOAO2666/processoseletivoIoT/actions/jobs/88109580639/logs', headers={'User-Agent': 'Mozilla/5.0'})
try:
    resp = urllib.request.urlopen(req).read().decode('utf-8')
    print(resp)
except Exception as e:
    print(e)
