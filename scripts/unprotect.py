#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.request
from config import ROOT, load
cfg=load(sys.argv[1])
if cfg['environment']!='prd' or sys.argv[2]!=cfg['name']+':destroy':
    sys.exit('production destroy confirmation required')
host=json.loads((ROOT/'.runtime/prd/outputs.json').read_text())['host']['value']
if host['name']!=cfg['name']:sys.exit('host name mismatch')
req=urllib.request.Request(f'https://api.hetzner.cloud/v1/servers/{host["id"]}/actions/change_protection',data=b'{"delete":false,"rebuild":false}',headers={'Authorization':'Bearer '+os.environ['HCLOUD_TOKEN'],'Content-Type':'application/json'},method='POST')
with urllib.request.urlopen(req,timeout=30) as response:
    result=json.load(response)
    if result['action']['status']=='error':sys.exit('failed to disable deletion protection')

action=result['action']
for attempt in range(30):
    if action['status']=='success':break
    if action['status']=='error':sys.exit('failed to disable deletion protection')
    time.sleep(1)
    poll=urllib.request.Request(f'https://api.hetzner.cloud/v1/actions/{action["id"]}',headers={'Authorization':'Bearer '+os.environ['HCLOUD_TOKEN']})
    with urllib.request.urlopen(poll,timeout=30) as response:action=json.load(response)['action']
else:sys.exit('deletion protection change timed out; inspect provider action before retrying')
