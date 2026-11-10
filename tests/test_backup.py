"""Execute the rendered maintenance script against local fake Docker/Restic commands.
No cloud access and no Docker daemon. Assertions verify ordering and failure behavior.
"""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from jinja2 import Environment
ROOT=Path(__file__).resolve().parents[1]

MOCK=r'''#!/usr/bin/env python3
import json,os,pathlib,shutil,sys
args=sys.argv[1:];tool=pathlib.Path(sys.argv[0]).name
with open(os.environ['CALLS'],'a') as f:f.write(tool+' '+' '.join(args)+'\n')
if tool=='docker':
    if 'ps' in args and '--status' in args:print('odoo')
    if 'pg_dump' in args:
        if os.environ.get('FAIL_DUMP'):sys.exit(42)
        print('synthetic database dump')
    if 'pg_restore' in args and '--list' not in args and os.environ.get('FAIL_RESTORE'):sys.exit(43)
if tool=='restic':
    if args[0]=='cat' and os.environ.get('FAIL_AUTH'):sys.exit(44)
    if args[0]=='backup':
        if os.environ.get('FAIL_BACKUP'):sys.exit(45)
        storage=pathlib.Path(os.environ['STORAGE'])
        if storage.exists():shutil.rmtree(storage)
        shutil.copytree(args[1],storage)
        print('{"message_type":"summary","snapshot_id":"'+('a'*64)+'"}')
    if args[0]=='snapshots':print(json.dumps([{'tags':[os.environ.get('SNAPSHOT_TAG','test-odoo-dev')]}]))
    if args[0]=='restore':
        target=pathlib.Path(args[args.index('--target')+1])
        dest=target/pathlib.Path(os.environ['STACK']).relative_to('/')/'staging/snapshot'
        shutil.copytree(os.environ['STORAGE'],dest)
if tool=='sha256sum':
    if '--check' not in args:print('synthetic checksum')
sys.exit(0)
'''

class Backup(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.stack=self.root/'stack';self.stack.mkdir()
        for name in ['secrets','data','config','addons','state','staging']:(self.stack/name).mkdir()
        (self.stack/'secrets/backup.env').write_text('')
        (self.stack/'data/attachment').write_text('original attachment')
        (self.stack/'config/version.json').write_text(json.dumps({'environment':'dev','odoo_image':'synthetic'}))
        (self.stack/'compose.yml').write_text('synthetic')
        template=(ROOT/'ansible/roles/application/templates/backup.sh.j2').read_text()
        jinja=Environment();jinja.filters['quote']=shlex.quote
        script=jinja.from_string(template).render(name='test-odoo-dev',database='odoo',backup_keep_daily=7,backup_keep_weekly=4,backup_keep_monthly=6)
        script=script.replace('/opt/odoo',str(self.stack)).replace('/run/lock/odoo-maintenance.lock',str(self.root/'lock'))
        self.script=self.root/'backup.sh';self.script.write_text(script)
        self.bin=self.root/'bin';self.bin.mkdir()
        for name in ['docker','restic','flock','logger','sha256sum','chown']:
            path=self.bin/name;path.write_text(MOCK.replace('#!/usr/bin/env python3','#!'+os.sys.executable));path.chmod(0o755)
        self.calls=self.root/'calls'
        self.env={'PATH':str(self.bin)+os.pathsep+os.environ['PATH'],'CALLS':str(self.calls),'STORAGE':str(self.root/'repository'),'STACK':str(self.stack)}
    def run_script(self,*args,code=0):
        result=subprocess.run(['bash',str(self.script),*args],env=self.env,capture_output=True,text=True)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return self.calls.read_text()
    def test_backup_order(self):
        calls=self.run_script('backup')
        stop=calls.index('stop --timeout 120 odoo');dump=calls.index('pg_dump');start=calls.index('start odoo');upload=calls.index('restic backup')
        self.assertTrue(stop<dump<start<upload)
        self.assertTrue((self.root/'repository/data/attachment').exists())
        self.assertTrue((self.stack/'state/last-backup-success').exists())
    def test_dump_failure_resumes_application_and_does_not_upload(self):
        self.env['FAIL_DUMP']='1';calls=self.run_script('backup',code=42)
        self.assertIn('start odoo',calls);self.assertNotIn('restic backup',calls)
        self.assertTrue((self.stack/'state/backup-failed').exists())
    def test_bad_credentials_do_not_stop_application(self):
        self.env['FAIL_AUTH']='1';calls=self.run_script('backup',code=44)
        self.assertNotIn('stop --timeout',calls)
    def test_restore_wrong_confirmation_never_touches_database(self):
        calls=self.run_script('restore','a'*64,'wrong:restore',code=2)
        self.assertNotIn('dropdb',calls)
    def test_restore_wrong_tag_never_touches_database(self):
        self.env['SNAPSHOT_TAG']='different-environment';calls=self.run_script('restore','a'*64,'test-odoo-dev:restore',code=1)
        self.assertNotIn('dropdb',calls)
    def test_restore_takes_safety_backup_and_restores_matching_filestore(self):
        self.run_script('backup')
        (self.stack/'data/attachment').write_text('new attachment')
        calls=self.run_script('restore','a'*64,'test-odoo-dev:restore')
        self.assertEqual((self.stack/'data/attachment').read_text(),'original attachment')
        self.assertLess(calls.rindex('restic backup'),calls.index('dropdb'))
        self.assertIn('pg_restore -U postgres --exit-on-error',calls)
    def test_restore_safety_backup_failure_prevents_drop(self):
        self.run_script('backup');self.env['FAIL_BACKUP']='1'
        calls=self.run_script('restore','a'*64,'test-odoo-dev:restore',code=45)
        self.assertNotIn('dropdb',calls)
    def test_partial_restore_keeps_application_offline(self):
        self.run_script('backup');self.env['FAIL_RESTORE']='1'
        calls=self.run_script('restore','a'*64,'test-odoo-dev:restore',code=43)
        after_drop=calls[calls.index('dropdb'):]
        self.assertNotIn('start odoo',after_drop);self.assertNotIn('up -d',after_drop)

if __name__=='__main__':unittest.main()
