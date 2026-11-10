#!/usr/bin/env python3
import os
import sys
import urllib.request
from config import load
from bootstrap import request
cfg=load(sys.argv[1])
checks=[('HCLOUD_TOKEN','https://api.hetzner.cloud/v1/servers'),('CLOUDFLARE_API_TOKEN','https://api.cloudflare.com/client/v4/user/tokens/verify')]
for key,url in checks:
    token=os.environ.get(key)
    if not token:sys.exit(f'missing {key}')
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':'Bearer '+token}),timeout=20) as response:
            if response.status!=200:sys.exit(f'{key} check failed')
    except Exception:sys.exit(f'{key} authentication/network check failed')
request('GET','organizations/'+cfg['hcp_organization'])
for key in ['AWS_ACCESS_KEY_ID','AWS_SECRET_ACCESS_KEY','BACKUP_AWS_ACCESS_KEY_ID','BACKUP_AWS_SECRET_ACCESS_KEY','RESTIC_PASSWORD','DB_PASSWORD','PG_ADMIN_PASSWORD','ODOO_MASTER_PASSWORD','ODOO_ADMIN_PASSWORD','CF_DNS_API_TOKEN']:
    if not os.environ.get(key):sys.exit(f'missing {key}')
print('Configuration and read-only provider authentication checks passed; S3 write/restore needs an integration drill.')
