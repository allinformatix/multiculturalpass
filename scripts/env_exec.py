#!/usr/bin/env python3
"""Hydrate the existing Bash orchestrator without shell evaluation or secret argv."""
import os
import sys
from config import load
from environment import effective, ConfigError
try:
    cfg=load(sys.argv[1]);data=effective(sys.argv[1],cfg,require_file=os.environ.get('CI')!='true')
    child=os.environ.copy()
    # Export secrets plus explicitly supplied values; derived nonsecrets are already in config.json.
    from environment import registry
    for key,spec in registry().items():
        if spec['secret'] and data[key]:child[key]=data[key]
    child['OPS_ENV_READY']='1'
    if data['SSH_PRIVATE_KEY_PATH']:
        from pathlib import Path
        key=Path(data['SSH_PRIVATE_KEY_PATH']).expanduser()
        if not key.is_file() or key.stat().st_mode&0o077:raise ConfigError('private SSH key path missing or permissions too broad')
        child['OPS_SSH_KEY_PATH']=str(key)
    if data['GRAFANA_CLOUD_LOKI_USER']:child['GRAFANA_CLOUD_LOKI_USER']=data['GRAFANA_CLOUD_LOKI_USER']
    if data['BOOTSTRAP_SSH_USER']:child['BOOTSTRAP_SSH_USER']=data['BOOTSTRAP_SSH_USER']
    os.execvpe('bash',['bash',str(__import__('environment').ROOT/'ops.sh'),*sys.argv[2:]],child)
except (ValueError,KeyError,OSError) as error:
    sys.exit('configuration error: '+str(error))
