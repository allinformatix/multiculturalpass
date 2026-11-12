#!/usr/bin/env python3
"""Offline baseline scanner; prints filenames only, never matched credential values."""
from pathlib import Path
import re
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'\bAKIA[0-9A-Z]{16}\b',r'\bgh[pousr]_[A-Za-z0-9]{30,}\b',r'\bgithub_pat_[A-Za-z0-9_]{40,}\b']
failed=[]
listing=subprocess.run(['git','-C',str(ROOT),'ls-files','--cached','--others','--exclude-standard','-z'],capture_output=True,check=False)
if listing.returncode:sys.exit('Secret scan requires a Git checkout')
for relative in set(listing.stdout.decode().split('\0'))- {''}:
    path=ROOT/relative
    if not path.is_file():continue
    if path.suffix in ('.pem','.key','.tfstate') or (path.name.startswith('.env') and path.name!='.env.example'):
        failed.append(str(path.relative_to(ROOT)));continue
    try:text=path.read_text()
    except UnicodeError:continue
    if any(re.search(p,text) for p in patterns):failed.append(str(path.relative_to(ROOT)))
if failed:sys.exit('Possible committed secrets in: '+', '.join(failed))
print('Baseline secret scan passed (known key/token patterns; not proof of absence).')
