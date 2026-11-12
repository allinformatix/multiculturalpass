#!/usr/bin/env python3
"""Read pinned binary versions; GitHub Actions consume the same registry as installers."""
import json
import os
from pathlib import Path
import re
import sys
from prerequisites import tool_registry
versions={key:spec['version'] for key,spec in tool_registry().items() if spec.get('version')}
if any(not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',value) for value in versions.values()):sys.exit('invalid tool version in registry')
if '--github-output' in sys.argv:
    with Path(os.environ['GITHUB_OUTPUT']).open('a') as stream:
        for key,value in versions.items():stream.write(key+'='+value+'\n')
else:print(json.dumps(versions))
