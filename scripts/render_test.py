#!/usr/bin/env python3
"""Render real Ansible Jinja templates with synthetic credentials for offline validation."""
import json
import os
from pathlib import Path
import subprocess
import sys
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar, trust_as_template
from config import ROOT

out=ROOT/'.runtime/rendered';out.mkdir(parents=True,exist_ok=True)
config=json.loads((ROOT/'config/defaults.json').read_text())
config['cloudflare_cidrs']=json.loads((ROOT/'config/cloudflare-ips.json').read_text())
config.update(name='test-odoo-dev',environment='dev',hostname='odoo.sample.org',acme_email='ops@sample.org',backup_bucket='test-odoo-dev-backups',odoo_root='/opt/odoo')
for key in ['DB_PASSWORD','PG_ADMIN_PASSWORD','ODOO_MASTER_PASSWORD','ODOO_ADMIN_PASSWORD','RESTIC_PASSWORD','BACKUP_AWS_ACCESS_KEY_ID','BACKUP_AWS_SECRET_ACCESS_KEY','CF_DNS_API_TOKEN']:
    os.environ[key]='0'*40
# Load Ansible's built-in lookup/filter plugins through its normal collection initialization.
from ansible.plugins.loader import init_plugin_loader
init_plugin_loader()
templar=Templar(loader=DataLoader(),variables=config)
for path in (ROOT/'ansible/roles/application/templates').glob('*.j2'):
    value=templar.template(trust_as_template(path.read_text()),preserve_trailing_newlines=True)
    (out/path.stem).write_text(value)
for path in out.glob('*.sh'):subprocess.run(['bash','-n',str(path)],check=True)
compose=out/'compose.yml'
for directory in ['secrets','config','data','addons']:(out/directory).mkdir(exist_ok=True)
(out/'secrets/pg_admin_password').write_text('0'*40)
subprocess.run(['docker','compose','-f',str(compose),'config','--quiet'],check=True)
print('Ansible templates rendered; Bash and Docker Compose validation passed.')
