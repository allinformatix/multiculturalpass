#!/usr/bin/env python3
import json
import subprocess
import sys
if sys.argv[1] == 'prd':
    plan=json.loads(subprocess.check_output(['terraform','-chdir='+sys.argv[3],'show','-json',sys.argv[2]]))
    if any('delete' in r['change']['actions'] for r in plan.get('resource_changes',[])):
        sys.exit('production plan contains deletion/replacement; perform a separately reviewed migration')
