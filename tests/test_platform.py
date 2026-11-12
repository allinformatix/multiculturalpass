import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import environment as env
import prerequisites as tools
import github_config as gh
import preflight
import config
import platform_ops
ROOT=Path(__file__).resolve().parents[1]

class Platform(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);shutil.copytree(ROOT/'config',self.root/'config',ignore=shutil.ignore_patterns('project.json'))
        for module in [env,tools,gh,config,platform_ops]:
            p=patch.object(module,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{},clear=True);p.start();self.addCleanup(p.stop)
        self.cfg={'name':'test-dev','slug':'test','environment':'dev','tenant_id':'customer','cloud_provider':'hetzner','region':'fsn1','backup_bucket':'test-dev-backups','observability_enabled':False,'github_repository':'owner/repo'}
    def dotenv(self,text,mode=0o600):
        p=self.root/'.env.dev';p.write_text(text);p.chmod(mode);return p
    def test_platform_macos_intel(self):self.assertEqual(tools.platform_info('Darwin','x86_64')['architecture'],'amd64')
    def test_platform_macos_arm(self):self.assertTrue(tools.platform_info('Darwin','arm64')['supported'])
    def test_platform_ubuntu_arm(self):self.assertTrue(tools.platform_info('Linux','aarch64','ID=ubuntu')['supported'])
    def test_platform_debian_intel(self):self.assertTrue(tools.platform_info('Linux','x86_64','ID=debian')['supported'])
    def test_platform_unknown_rejected(self):self.assertFalse(tools.platform_info('Linux','x86_64','ID=fedora')['supported'])
    def test_ci_repository_identity_rejected(self):
        with self.assertRaises(env.ConfigError):preflight.run({'GITHUB_REPOSITORY':'other/repo'},self.cfg,'plan',ci=True,network=False)
    def test_versions_numeric(self):self.assertGreater(tools.version('1.13.5'),tools.version('1.9.0'))
    def test_tool_missing(self):
        with patch.object(tools.shutil,'which',return_value=None):self.assertEqual(tools.detect('gh',tools.tool_registry()['gh'],True)['status'],'missing')
    def test_tool_version_unsupported(self):
        with patch.object(tools.shutil,'which',return_value='/gh'),patch.object(tools.subprocess,'run',return_value=Mock(stdout='gh version 1.0.0',stderr='',returncode=0)):
            self.assertEqual(tools.detect('gh',tools.tool_registry()['gh'],True)['status'],'unsupported')
    def test_hetzner_uses_no_optional_cli(self):
        selected=tools.contexts('deploy')
        for key in ['aws','az','gcloud','hcloud','doctl','jq','yq']:
            self.assertFalse(set(tools.tool_registry()[key]['contexts'])&selected)
    def test_no_local_docker_for_remote_deploy(self):self.assertNotIn('compose',tools.contexts('deploy'))
    def test_install_idempotent(self):
        with patch.object(tools,'detect',return_value={'status':'ok'}),patch.object(tools.subprocess,'run') as run:
            self.assertEqual(tools.install('gh')['status'],'unchanged');run.assert_not_called()
    def test_install_requires_policy(self):
        with patch.object(tools,'detect',return_value={'status':'missing','path':None}):
            with self.assertRaises(tools.PrerequisiteError):tools.install('gh')
    def test_no_implicit_upgrade(self):
        with patch.object(tools,'detect',return_value={'status':'unsupported','path':'/gh'}):
            with self.assertRaises(tools.PrerequisiteError):tools.install('gh',allow_install=True)
    def test_apt_requires_system_permission_before_sudo(self):
        with patch.object(tools,'detect',return_value={'status':'missing','path':None}),patch.object(tools,'platform_info',return_value={'supported':True,'package_manager':'apt-get'}),patch.object(tools.subprocess,'run') as run:
            with self.assertRaises(tools.PrerequisiteError):tools.install('gh',allow_install=True)
            run.assert_not_called()
    def test_bad_checksum_prevents_install(self):
        with patch.object(tools,'detect',return_value={'status':'missing','path':None}),patch.object(tools,'platform_info',return_value={'supported':True,'os':'Linux','architecture':'arm64'}),patch.object(tools,'download',side_effect=[b'0000  terraform_1.13.5_linux_arm64.zip',b'bad']):
            with self.assertRaisesRegex(tools.PrerequisiteError,'checksum mismatch'):tools.install('terraform',allow_install=True)
        self.assertFalse((self.root/'.runtime/tools/bin/terraform').exists())
    def test_missing_env_has_actionable_error(self):
        with self.assertRaisesRegex(env.ConfigError,'env init'):env.values('dev',require_file=True)
    def test_parser_preserves_quoted_literal(self):self.assertEqual(env.parse(self.dotenv("RESTIC_PASSWORD='some literal value'\n"))['RESTIC_PASSWORD'],'some literal value')
    def test_parser_rejects_command_substitution(self):
        with self.assertRaises(env.ConfigError):env.parse(self.dotenv('RESTIC_PASSWORD=$(touch /tmp/unsafe)\n'))
    def test_parser_rejects_backticks(self):
        with self.assertRaises(env.ConfigError):env.parse(self.dotenv('RESTIC_PASSWORD=`id`\n'))
    def test_parser_rejects_unknown(self):
        with self.assertRaises(env.ConfigError):env.parse(self.dotenv('EVIL=example\n'))
    def test_parser_rejects_duplicate(self):
        with self.assertRaises(env.ConfigError):env.parse(self.dotenv('ENVIRONMENT=dev\nENVIRONMENT=prd\n'))
    def test_parser_requires_private_permissions(self):
        with self.assertRaises(env.ConfigError):env.parse(self.dotenv('ENVIRONMENT=dev\n',0o644))
    def test_environment_identity(self):
        self.dotenv('ENVIRONMENT=prd\n')
        with self.assertRaises(env.ConfigError):env.values('dev')
    def test_process_takes_precedence(self):
        self.dotenv('ODOO_WORKERS=1\n');self.assertEqual(env.values('dev',process={'ODOO_WORKERS':'2'})['ODOO_WORKERS'],'2')
    def test_ci_never_reads_dotenv(self):
        self.dotenv('THIS_IS_NOT_ALLOWED=$(id)\n');self.assertEqual(env.values('dev',True,{'CI':'true'})['ENVIRONMENT'],'dev')
    def test_alias_conflicts_fail(self):
        with self.assertRaises(env.ConfigError):env.values('dev',process={'DB_PASSWORD':'a'*32,'POSTGRES_PASSWORD':'b'*32})
    def test_init_preserves_existing_file(self):
        p=self.dotenv('ENVIRONMENT=dev\n')
        with self.assertRaises(env.ConfigError):env.initialize('dev')
        self.assertEqual(p.read_text(),'ENVIRONMENT=dev\n')
    def test_init_private_generated_file(self):
        with patch.object(config,'load',side_effect=ValueError()):env.initialize('dev')
        self.assertEqual((self.root/'.env.dev').stat().st_mode&0o777,0o600)
        self.assertEqual(env.parse(self.root/'.env.dev')['ENVIRONMENT'],'dev')
    def test_example_is_registry_complete(self):
        values=env.parse(self.dotenv(env.example()))
        self.assertEqual(set(values),set(env.registry()))
    def test_missing_secrets(self):
        with self.assertRaisesRegex(env.ConfigError,'HCLOUD_TOKEN'):env.validate(env.values('dev'),{'infra'},self.cfg)
    def obs_data(self,url):
        data=env.values('dev');data.update(GRAFANA_CLOUD_LOKI_URL=url,GRAFANA_CLOUD_LOKI_USER='1234',GRAFANA_CLOUD_LOKI_TOKEN='synthetic-not-real-token')
        return data
    def test_bad_loki_http(self):
        self.cfg['observability_enabled']=True
        with self.assertRaises(env.ConfigError):env.validate(self.obs_data('http://logs-prod-001.grafana.net/loki/api/v1/push'),set(),self.cfg)
    def test_loki_query_rejected(self):
        self.cfg['observability_enabled']=True
        with self.assertRaises(env.ConfigError):env.validate(self.obs_data('https://logs-prod-001.grafana.net/loki/api/v1/push?token=unsafe'),set(),self.cfg)
    def test_loki_valid(self):
        self.cfg['observability_enabled']=True;env.validate(self.obs_data('https://logs-prod-001.grafana.net/loki/api/v1/push'),set(),self.cfg)
    def test_loki_missing_token(self):
        self.cfg['observability_enabled']=True;data=self.obs_data('https://logs-prod-001.grafana.net/loki/api/v1/push');data['GRAFANA_CLOUD_LOKI_TOKEN']=''
        with self.assertRaises(env.ConfigError):env.validate(data,set(),self.cfg)
    def test_github_api_failure_redacts_stderr(self):
        with patch.object(gh.subprocess,'run',return_value=Mock(returncode=1,stderr='secret-data HTTP 403',stdout='')):
            with self.assertRaises(gh.GitHubError) as caught:gh.api('repos/owner/repo')
            self.assertNotIn('secret-data',str(caught.exception))
    def test_github_present_secret_is_not_value_validation(self):
        with patch.object(gh,'api',return_value=[{}]),patch.object(gh,'inventory',return_value=({'HCLOUD_TOKEN':{'scope':'environment'}},[])):
            result=gh.check({},self.cfg,'secret',{'infra'})['checks']
            self.assertEqual(next(r for r in result if r['name']=='HCLOUD_TOKEN')['status'],'present-value-unverifiable')
    def test_github_unreadable_scope_is_unknown(self):
        with patch.object(gh,'api',return_value=[{}]),patch.object(gh,'inventory',return_value=({},['organization'])):
            self.assertTrue(all(r['status']=='unknown-permissions' for r in gh.check({},self.cfg,'secret',{'infra'})['checks']))
    def test_github_existing_secret_retained(self):
        with patch.object(gh,'api',return_value=[{}]),patch.object(gh,'inventory',return_value=({'HCLOUD_TOKEN':{'scope':'environment'}},[])),patch.object(gh.subprocess,'run') as run:
            result=gh.sync({'HCLOUD_TOKEN':'synthetic-not-real'},self.cfg);run.assert_not_called();self.assertEqual(result[0]['status'],'retained')
    def test_github_sync_uses_stdin_only(self):
        secret='synthetic-never-a-real-token'
        with patch.object(gh,'api',return_value=[{}]),patch.object(gh,'inventory',return_value=({},[])),patch.object(gh.subprocess,'run',return_value=Mock(returncode=0)) as run:
            gh.sync({'HCLOUD_TOKEN':secret},self.cfg)
            self.assertNotIn(secret,str(run.call_args.args));self.assertEqual(run.call_args.kwargs['input'],secret)
    def test_github_prd_sync_requires_confirmation(self):
        self.cfg.update(environment='prd',name='test-prd')
        with self.assertRaises(env.ConfigError):gh.sync({},self.cfg,dry_run=True)
    def test_unknown_variables_not_synced(self):
        with patch.object(gh,'api',return_value=[{}]),patch.object(gh,'inventory',return_value=({},[])),patch.object(gh.subprocess,'run') as run:
            gh.sync({'UNKNOWN':'sensitive','GH_TOKEN':'sensitive'},self.cfg);run.assert_not_called()
    def test_env_init_dry_run_does_not_write(self):
        self.assertEqual(env.initialize('dev',dry_run=True)['status'],'would-create')
        self.assertFalse((self.root/'.env.dev').exists())
    def test_verified_install_writes_only_user_binary(self):
        import zipfile
        import hashlib
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,'w') as bundle:bundle.writestr('terraform',b'synthetic binary')
        raw=archive.getvalue();manifest=(hashlib.sha256(raw).hexdigest()+'  terraform_1.13.5_linux_arm64.zip').encode()
        with patch.object(tools,'detect',side_effect=[{'status':'missing','path':None},{'status':'ok'}]),patch.object(tools,'platform_info',return_value={'supported':True,'os':'Linux','architecture':'arm64'}),patch.object(tools,'download',side_effect=[manifest,raw]):
            self.assertEqual(tools.install('terraform',allow_install=True)['status'],'ok')
        self.assertEqual((self.root/'.runtime/tools/bin/terraform').read_bytes(),b'synthetic binary')
    def test_ignored_dotenv_is_not_reported_committed(self):
        scripts=self.root/'scripts';scripts.mkdir();shutil.copy(ROOT/'scripts/scan_secrets.py',scripts/'scan_secrets.py')
        (self.root/'.gitignore').write_text('.env*\n')
        self.dotenv('HCLOUD_TOKEN=synthetic-local-only-token\n')
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        result=subprocess.run([sys.executable,str(scripts/'scan_secrets.py')],capture_output=True)
        self.assertEqual(result.returncode,0)
    def test_tracked_dotenv_is_rejected_even_if_ignored(self):
        scripts=self.root/'scripts';scripts.mkdir();shutil.copy(ROOT/'scripts/scan_secrets.py',scripts/'scan_secrets.py')
        (self.root/'.gitignore').write_text('.env*\n');self.dotenv('HCLOUD_TOKEN=synthetic-local-only-token\n')
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        subprocess.run(['git','-C',str(self.root),'add','-f','.env.dev'],check=True)
        result=subprocess.run([sys.executable,str(scripts/'scan_secrets.py')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertNotIn('synthetic-local-only-token',result.stdout+result.stderr)
    def test_workflow_registry_coverage(self):
        with patch.object(gh,'ROOT',ROOT):self.assertEqual(gh.audit_workflows()['workflow_registry'],'ok')
    def test_alloy_labels_and_no_docker_socket(self):
        source=(ROOT/'ansible/roles/observability/templates/config.alloy.j2').read_text()
        for label in ['tenant','stage','project','application','provider','region']:self.assertIn(label+' =',source)
        self.assertNotIn('docker.sock',source)
    def test_doctor_json_without_environment_never_networks(self):
        with patch.object(tools,'inspect',return_value=[]),patch.object(tools,'platform_info',return_value={'distribution':'debian','architecture':'arm64','supported':True,'package_manager':'apt-get','uid':1000}),patch.object(preflight,'cloud_checks') as network,contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(platform_ops.main(['doctor','--json']),0);network.assert_not_called();json.loads(output.getvalue())

if __name__=='__main__':unittest.main()
