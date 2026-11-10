import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class CLI(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for directory in ['lib','scripts','config']:
            shutil.copytree(ROOT/directory,self.root/directory,ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(ROOT/'ops.sh',self.root/'ops.sh')
        cfg=json.loads((self.root/'config/project.example.json').read_text())
        cfg.update(slug='test-odoo',hcp_organization='test-org',ssh_public_key='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleTestKey',acme_email='ops@sample.org')
        (self.root/'config/project.json').write_text(json.dumps(cfg))
        for env in ['dev','stg','prd']:
            cfg={'hostname':f'odoo.{env}.sample.org','cloudflare_zone_id':'a'*32,'ssh_cidrs':['198.51.100.7/32'],'external_cache_bypass_confirmed':True}
            (self.root/f'config/environments/{env}.json').write_text(json.dumps(cfg))
            (self.root/f'terraform/environments/{env}').mkdir(parents=True)
        self.bin=self.root/'bin';self.bin.mkdir()
        self.log=self.root/'calls'
        for name in ['terraform','ansible-playbook','ssh','curl','gh']:
            p=self.bin/name
            p.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$MOCK_LOG"\nexit "${MOCK_EXIT:-0}"\n');p.chmod(0o755)
        self.env={'PATH':str(self.bin)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'],'HOME':str(self.root),'MOCK_LOG':str(self.log)}
    def cli(self,*args,code=0):
        result=subprocess.run(['bash',str(self.root/'ops.sh'),*args],env=self.env,text=True,capture_output=True)
        self.assertEqual(result.returncode,code,result.stdout+result.stderr)
        return result.stdout+result.stderr
    def no_remote_calls(self):self.assertFalse(self.log.exists())
    def test_help(self):self.assertIn('Usage:',self.cli('--help'))
    def test_missing_environment(self):self.cli('plan',code=2);self.no_remote_calls()
    def test_invalid_environment(self):self.cli('plan','--env','../../prd',code=2);self.no_remote_calls()
    def test_missing_flag_value(self):self.cli('plan','--env',code=2)
    def test_unknown_command(self):self.cli('erase','--env','dev',code=2)
    def test_unknown_flag(self):self.cli('plan','--env','dev','--force',code=2)
    def test_plan_dry_run(self):
        out=self.cli('plan','--env','dev','--dry-run');self.assertIn('plan',out);self.no_remote_calls()
    def test_init_dry_run(self):self.cli('init','--env','dev','--dry-run');self.no_remote_calls()
    def test_deploy_dry_run(self):self.cli('deploy','--env','dev','--dry-run','--confirm','test-odoo-dev:apply');self.no_remote_calls()
    def test_app_only(self):
        out=self.cli('deploy','--env','dev','--app-only','--dry-run');self.assertNotIn('tfplan',out);self.no_remote_calls()
    def test_restore_missing_confirmation(self):self.cli('restore','--env','prd','--snapshot','a'*64,code=2);self.no_remote_calls()
    def test_restore_invalid_snapshot(self):self.cli('restore','--env','dev','--snapshot','latest','--confirm','test-odoo-dev:restore',code=2);self.no_remote_calls()
    def test_restore_other_environment_confirmation(self):self.cli('restore','--env','prd','--snapshot','a'*64,'--confirm','test-odoo-dev:restore',code=2);self.no_remote_calls()
    def test_restore_valid_dry(self):self.cli('restore','--env','dev','--snapshot','a'*64,'--confirm','test-odoo-dev:restore','--dry-run');self.no_remote_calls()
    def test_destroy_missing_confirmation(self):self.cli('destroy','--env','dev',code=2);self.no_remote_calls()
    def test_destroy_production_needs_extra_flag(self):self.cli('destroy','--env','prd','--confirm','test-odoo-prd:destroy',code=2);self.no_remote_calls()
    def test_destroy_dev_dry(self):
        out=self.cli('destroy','--env','dev','--confirm','test-odoo-dev:destroy','--dry-run');self.assertIn('-target=module.compute',out);self.assertNotIn('-target=module.backup',out);self.no_remote_calls()
    def test_terraform_failure_propagates(self):self.env['MOCK_EXIT']='31';self.cli('plan','--env','dev',code=31)
    def test_apply_needs_confirmation(self):self.cli('apply','--env','dev',code=2);self.no_remote_calls()
    def test_apply_missing_saved_plan_fails(self):
        self.cli('apply','--env','dev','--confirm','test-odoo-dev:apply',code=1)
        self.assertNotIn('apply -input',self.log.read_text())
    def test_config_rejects_unknown_secret_field(self):
        path=self.root/'config/project.json';cfg=json.loads(path.read_text());cfg['password']='unsafe';path.write_text(json.dumps(cfg));self.cli('plan','--env','dev',code=1)
    def test_open_ssh_rejected(self):
        path=self.root/'config/environments/dev.json';cfg=json.loads(path.read_text());cfg['ssh_cidrs']=['0.0.0.0/0'];path.write_text(json.dumps(cfg));self.cli('plan','--env','dev',code=1)
    def test_shared_hcp_workspace_rejected(self):
        path=self.root/'config/environments/dev.json';cfg=json.loads(path.read_text());cfg['hcp_workspace']='test-odoo-prd';path.write_text(json.dumps(cfg));self.cli('plan','--env','dev',code=1);self.no_remote_calls()
    def test_shared_hostname_rejected(self):
        path=self.root/'config/environments/dev.json';cfg=json.loads(path.read_text());cfg['hostname']='odoo.prd.sample.org';path.write_text(json.dumps(cfg));self.cli('plan','--env','dev',code=1);self.no_remote_calls()
    def test_major_migration_rejected(self):
        path=self.root/'config/environments/dev.json';cfg=json.loads(path.read_text());cfg['odoo_image']='odoo:19.0';path.write_text(json.dumps(cfg));self.cli('update','--env','dev',code=1);self.no_remote_calls()
    def test_unacknowledged_cache_rejected(self):
        path=self.root/'config/environments/dev.json';cfg=json.loads(path.read_text());cfg['external_cache_bypass_confirmed']=False;path.write_text(json.dumps(cfg));self.cli('plan','--env','dev',code=1)
    def test_plan_guard_rejects_prd_delete(self):
        p=self.bin/'terraform';p.write_text('#!/bin/sh\nprintf \'%s\' \'{"resource_changes":[{"change":{"actions":["delete","create"]}}]}\'\n');p.chmod(0o755)
        result=subprocess.run([sys.executable,str(ROOT/'scripts/check_plan.py'),'prd','unused','unused'],env=self.env,capture_output=True)
        self.assertEqual(result.returncode,1)

if __name__=='__main__':unittest.main()
