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
config['alloy_version']=json.loads((ROOT/'config/tools.json').read_text())['tools']['alloy']['version']+'-1'
config['tenant_id']='test-customer'
config['loki_url']='https://logs-prod-001.grafana.net/loki/api/v1/push'
config.update(slug='test-odoo',name='test-odoo-dev',environment='dev',hostname='odoo.sample.org',acme_email='ops@sample.org',backup_bucket='test-odoo-dev-backups',odoo_root='/opt/odoo')
for key in ['DB_PASSWORD','PG_ADMIN_PASSWORD','ODOO_MASTER_PASSWORD','ODOO_ADMIN_PASSWORD','RESTIC_PASSWORD','BACKUP_AWS_ACCESS_KEY_ID','BACKUP_AWS_SECRET_ACCESS_KEY','CF_DNS_API_TOKEN','GRAFANA_CLOUD_LOKI_USER','GRAFANA_CLOUD_LOKI_TOKEN']:
    os.environ[key]='0'*40
# Load Ansible's built-in lookup/filter plugins through its normal collection initialization.
from ansible.plugins.loader import init_plugin_loader
init_plugin_loader()
templar=Templar(loader=DataLoader(),variables=config)
for path in list((ROOT/'ansible/roles/application/templates').glob('*.j2'))+list((ROOT/'ansible/roles/observability/templates').glob('*.j2')):
    value=templar.template(trust_as_template(path.read_text()),preserve_trailing_newlines=True)
    (out/path.stem).write_text(value)
for path in out.glob('*.sh'):subprocess.run(['bash','-n',str(path)],check=True)
compose=out/'compose.yml'
for directory in ['secrets','config','data','addons']:(out/directory).mkdir(exist_ok=True)
(out/'secrets/pg_admin_password').write_text('0'*40)
subprocess.run(['docker','compose','-f',str(compose),'config','--quiet'],check=True)
print('Ansible templates rendered; Bash and Docker Compose validation passed.')

# Validate both deployment modes and the privacy/network contracts, not just YAML syntax.
import yaml
for enabled in (False,True):
    mode={**config,'observability_enabled':enabled}
    renderer=Templar(loader=DataLoader(),variables=mode)
    rendered=renderer.template(trust_as_template((ROOT/'ansible/roles/application/templates/compose.yml.j2').read_text()),preserve_trailing_newlines=True)
    path=out/('compose-observability-'+str(enabled).lower()+'.yml');path.write_text(rendered)
    services=yaml.safe_load(rendered)['services']
    if services['db'].get('ports'):raise SystemExit('PostgreSQL must not expose host ports')
    for service,component in [('db','postgres'),('odoo','odoo')]:
        actual=services[service]['logging']
        if actual['driver']!=('journald' if enabled else 'local'):raise SystemExit('incorrect log driver for '+service)
        if enabled and actual['options']['tag']!=component:raise SystemExit('incorrect journal component tag')
        if services[service]['labels']['ops.tenant']!='test-customer':raise SystemExit('tenant label mismatch')
    subprocess.run(['docker','compose','-f',str(path),'config','--quiet'],check=True)
print('Enabled and disabled observability Compose variants and component tags passed.')
