#!/usr/bin/env python3
"""Offline baseline scanner; prints filenames only, never matched credential values."""
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\bAKIA[0-9A-Z]{16}\b',r'\bgh[pousr]_[A-Za-z0-9]{30,}\b',r'\bgithub_pat_[A-Za-z0-9_]{40,}\b']
failed=[]
for path in ROOT.rglob('*'):
    if any(p in {'.git','.runtime','.venv','.terraform','__pycache__'} for p in path.parts):continue
    if not path.is_file():continue
    if path.suffix in ('.pem','.key','.tfstate') or path.name.startswith('.env'):
        failed.append(str(path.relative_to(ROOT)));continue
    try:text=path.read_text()
    except UnicodeError:continue
    if any(re.search(p,text) for p in patterns):failed.append(str(path.relative_to(ROOT)))
if failed:sys.exit('Possible committed secrets in: '+', '.join(failed))
print('Baseline secret scan passed (known key/token patterns; not proof of absence).')
