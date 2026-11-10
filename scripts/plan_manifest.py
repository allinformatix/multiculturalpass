#!/usr/bin/env python3
import hashlib
import json
import sys
from config import ROOT, load
config=load(sys.argv[1])
target=ROOT/'.runtime'/config['environment']
h=hashlib.sha256(json.dumps(config,sort_keys=True).encode())
for path in sorted((ROOT/'terraform').rglob('*.tf')):
    if '.terraform' not in path.parts:
        h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
h.update((target/'apply.tfplan').read_bytes())
path=target/'plan.sha256'
if sys.argv[2]=='write':path.write_text(h.hexdigest()+'\n')
elif sys.argv[2]!='check' or path.read_text().strip()!=h.hexdigest():
    sys.exit('Plan/configuration mismatch; generate and review a new plan')
