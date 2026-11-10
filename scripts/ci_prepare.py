#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import sys
from config import ROOT

env=sys.argv[1]
if env not in ('dev','stg','prd'):sys.exit('invalid environment')
for variable,target in [('PROJECT_CONFIG',ROOT/'config/project.json'),('ENVIRONMENT_CONFIG',ROOT/f'config/environments/{env}.json')]:
    value=json.loads(os.environ[variable])
    if not isinstance(value,dict):sys.exit('expected JSON object')
    target.write_text(json.dumps(value))
if os.environ.get('REQUIRE_SSH','true')=='true':
    ssh=Path.home()/'.ssh';ssh.mkdir(mode=0o700,exist_ok=True)
    for variable,filename in [('SSH_PRIVATE_KEY','id_ed25519'),('SSH_KNOWN_HOSTS','known_hosts')]:
        if not os.environ.get(variable):sys.exit(f'missing {variable}')
        path=ssh/filename;path.write_text(os.environ[variable]+'\n');path.chmod(0o600)
if env=='prd':
    result=json.loads(subprocess.check_output(['gh','api',f'repos/{os.environ["GITHUB_REPOSITORY"]}/environments/prd']))
    if not any(rule.get('type')=='required_reviewers' and rule.get('reviewers') for rule in result.get('protection_rules',[])):
        sys.exit('prd requires GitHub Environment reviewers; configure protection before running')
