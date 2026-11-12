#!/usr/bin/env python3
"""Compatibility entry point; all Doctor behavior lives in the shared ops management layer."""
import os
from pathlib import Path
import sys
arguments=['doctor']
if len(sys.argv)>1:arguments+=['--env',sys.argv[1],*sys.argv[2:]]
os.execvpe(sys.executable,[sys.executable,str(Path(__file__).with_name('platform_ops.py')),*arguments],os.environ)
