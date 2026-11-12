#!/usr/bin/env python3
"""Verify the journal -> collector -> Loki path; requires a separate read-capable token."""
import json
import os
import re
import sys
import time
import urllib.parse
from config import load
from environment import effective, ConfigError
from preflight import request, AuthenticationError
try:
    cfg=load(sys.argv[1]);data=effective(sys.argv[1],cfg)
    token=data.get('GRAFANA_CLOUD_LOKI_READ_TOKEN')
    if not token:raise ConfigError('GRAFANA_CLOUD_LOKI_READ_TOKEN with logs:read is required to verify ingestion; write token alone cannot prove delivery')
    nonce=sys.argv[2]
    if not re.fullmatch('[a-f0-9]{16}',nonce):raise ConfigError('invalid delivery marker')
    query='{tenant='+json.dumps(cfg['tenant_id'])+',stage='+json.dumps(cfg['environment'])+',project='+json.dumps(cfg['slug'])+',component="deployment"} |= "observability delivery test '+nonce+'"'
    url=data['GRAFANA_CLOUD_LOKI_URL'].removesuffix('/push')+'/query_range?'+urllib.parse.urlencode({'query':query,'limit':'5','start':str(time.time_ns()-120*10**9)})
    for attempt in range(6):
        result=request(url,basic=(data['GRAFANA_CLOUD_LOKI_USER'],token))
        if result.get('data',{}).get('result'):
            print('Collector delivery marker found in Loki; log bodies intentionally omitted');break
        if attempt<5:time.sleep(5)
    else:raise AuthenticationError('marker not found in Loki; inspect collector, credentials, queue and labels')
except (ValueError,KeyError,OSError) as error:sys.exit(str(error))
