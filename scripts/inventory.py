#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
from config import ROOT, load
cfg=load(sys.argv[1]); target=ROOT/'.runtime'/cfg['environment']
host=json.loads((target/'outputs.json').read_text())['host']['value']
if host['environment']!=cfg['environment'] or host['name']!=cfg['name']:
    sys.exit('Terraform output environment/name mismatch')
user=os.environ.get('BOOTSTRAP_SSH_USER',cfg['ssh_user'])
if user not in ('root',cfg['ssh_user']):
    sys.exit('invalid bootstrap SSH user')
(target/'inventory.json').write_text(json.dumps({'all':{'hosts':{'odoo':{'ansible_host':host['ipv4'],'ansible_user':user}}}}))
