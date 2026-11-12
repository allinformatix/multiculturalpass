#!/usr/bin/env python3
"""Validate the rendered Alloy config and run its real redaction stages offline."""
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from environment import ROOT

binary=os.environ.get('ALLOY_BIN') or shutil.which('alloy')
if not binary:raise SystemExit('Alloy validation needs ALLOY_BIN or alloy on PATH; run prerequisites install --operation alloy-validation --allow-install')
source=ROOT/'.runtime/rendered/config.alloy'
subprocess.run([binary,'validate',str(source)],check=True)
text=source.read_text();start=text.index('loki.process "redact"');end=text.index('loki.source.journal',start)
pipeline=text[start:end].replace('loki.write.cloud.receiver','loki.echo.test.receiver')
with tempfile.TemporaryDirectory(prefix='alloy-offline-test-') as directory:
    root=Path(directory);fixture=root/'fixture.log'
    fixture.write_text('INFO safe-delivery-marker\nERROR password=never-export-this-value\nERROR https://sample.org/path?token=never-export-query\nINFO Authorization: Bearer never-export-header\nERROR email=synthetic@example.invalid address=192.0.2.123\n')
    config=root/'test.alloy'
    config.write_text('logging { level = "info" }\nloki.echo "test" {}\n'+pipeline+'\nloki.source.file "test" {\n targets = [{__path__ = '+json.dumps(str(fixture))+', component = "test"}]\n forward_to = [loki.process.redact.receiver]\n}\n')
    output=root/'output.log'
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    with output.open('w') as stream:
        process=subprocess.Popen([binary,'run','--server.http.listen-addr=127.0.0.1:'+str(port),'--disable-reporting','--storage.path='+str(root/'data'),str(config)],stdout=stream,stderr=subprocess.STDOUT)
        try:
            for _ in range(50):
                if process.poll() is not None:break
                if 'safe-delivery-marker' in output.read_text() and '[REDACTED]' in output.read_text():break
                time.sleep(0.1)
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
    result=output.read_text()
    # Never include potentially unredacted fixture output in diagnostics.
    if 'safe-delivery-marker' not in result or '[REDACTED]' not in result:
        sanitized=result
        for value in ('never-export-this-value','never-export-query','never-export-header','synthetic@example.invalid','192.0.2.123'):sanitized=sanitized.replace(value,'[FIXTURE]')
        raise SystemExit('offline Alloy pipeline failed; sanitized synthetic-fixture diagnostics: '+sanitized[:3000])
    if any(value in result for value in ('never-export-this-value','never-export-query','never-export-header','synthetic@example.invalid','192.0.2.123')):
        raise SystemExit('offline Alloy redaction failed; raw output withheld')
print('Alloy config and actual offline redaction pipeline passed; no external Loki endpoint contacted.')
