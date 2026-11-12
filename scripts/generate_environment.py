#!/usr/bin/env python3
"""Generate the public example and operator reference from the one variable registry."""
import sys
from environment import ROOT, example, registry
rows=['# Environment-Referenz (generiert)','','Quelle: config/variables.json. Nicht manuell ändern; `python3 scripts/generate_environment.py` ausführen.','','| Variable | Typ | Secret | Pflicht für | GitHub | Sync |','|---|---|---|---|---|---|']
for key,spec in registry().items():
    rows.append('| '+key+' | '+spec['type']+' | '+str(spec['secret']).lower()+' | '+(', '.join(spec['required_for']) or 'optional')+' | '+spec.get('github_name',key)+' ('+spec['github']+') | '+str(spec['sync']).lower()+' |')
outputs={ROOT/'.env.example':example(),ROOT/'docs/environment-reference.md':'\n'.join(rows)+'\n'}
for path,text in outputs.items():
    if '--check' in sys.argv:
        if not path.exists() or path.read_text()!=text:sys.exit('registry-derived artifact is stale: '+str(path.relative_to(ROOT)))
    else:path.write_text(text)
