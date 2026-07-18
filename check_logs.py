import urllib.request, json
req = urllib.request.Request('https://api.github.com/repos/JOAO2666/processoseletivoIoT/actions/runs', headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req).read().decode('utf-8')
data = json.loads(resp)
run_id = data['workflow_runs'][0]['id']
print(f'Latest Run ID: {run_id}')

jobs_url = data['workflow_runs'][0]['jobs_url']
req = urllib.request.Request(jobs_url, headers={'User-Agent': 'Mozilla/5.0'})
jobs_data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
for job in jobs_data['jobs']:
    print(f"Job: {job['name']} - Status: {job['status']} - Conclusion: {job['conclusion']}")
    if job['conclusion'] == 'failure':
        print(f"  Job ID: {job['id']}")
