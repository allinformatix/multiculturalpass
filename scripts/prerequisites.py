"""Platform/tool detection and explicitly authorized, verified installation."""
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from environment import ROOT, ConfigError

class PrerequisiteError(ValueError):
    pass

def version(value):
    match=re.search(r'(\d+)(?:\.(\d+))?(?:\.(\d+))?',value)
    if not match:return None
    return tuple(int(x or 0) for x in match.groups())

def platform_info(system=None,machine=None,release=None):
    system=system or platform.system();machine=machine or platform.machine()
    arch={'x86_64':'amd64','amd64':'amd64','arm64':'arm64','aarch64':'arm64'}.get(machine)
    distro='macos' if system=='Darwin' else ''
    if system=='Linux':
        release=release if release is not None else Path('/etc/os-release').read_text()
        distro=next((line.split('=',1)[1].strip('"') for line in release.splitlines() if line.startswith('ID=')),'unknown')
    supported=system=='Darwin' or system=='Linux' and distro in ('ubuntu','debian')
    return {'os':system,'architecture':arch or machine,'distribution':distro,'supported':bool(supported and arch),'package_manager':'brew' if system=='Darwin' and shutil.which('brew') else 'apt-get' if system=='Linux' and shutil.which('apt-get') else None,'uid':os.geteuid(),'sudo_available':bool(shutil.which('sudo'))}

def tool_registry():return json.loads((ROOT/'config/tools.json').read_text())['tools']

def contexts(operation):
    base={'base'}
    if operation in ('doctor','init','plan','apply','provision','deploy','configure','status','logs','backup','backup-init','restore','update','destroy','observability'):
        base|={'infra','network'}
    if operation in ('doctor','init','github'):base|={'github','network'}
    if operation in ('doctor','deploy','configure','update'):base|={'server','ssh'}
    if operation in ('status','logs','backup','backup-init','restore','destroy','observability'):base|={'ssh'}
    if operation=='validate':base|={'compose'}
    if operation=='alloy-validation':base.add('alloy-validation')
    return base

def detect(name,spec,selected):
    path=shutil.which(spec['command'][0])
    report={'name':name,'category':spec['category'],'selected':selected,'status':'skipped' if not selected else 'missing','path':path,'minimum':spec['minimum']}
    if not selected:return report
    if not path:return report
    if spec.get('presence_only'):
        report['status']='ok';return report
    try:
        proc=subprocess.run(spec['command'],capture_output=True,text=True,timeout=15,check=False)
        text=proc.stdout+proc.stderr
        if name=='terraform':
            try:found=version(json.loads(proc.stdout)['terraform_version'])
            except (ValueError,KeyError):found=None
        elif name=='ssh':found=version(text.replace('OpenSSH_',''))
        elif name=='ansible':found=version(re.search(r'core ([0-9.]+)',text).group(1)) if re.search(r'core ([0-9.]+)',text) else None
        else:found=version(text)
        report['version']='.'.join(map(str,found)) if found else None
        report['status']='ok' if found and found>=version(spec['minimum']) and (not spec.get('maximum') or found<version(spec['maximum'])) else 'unsupported'
    except (OSError,subprocess.TimeoutExpired):report['status']='error'
    return report

def inspect(operation='doctor'):
    selected=contexts(operation)
    return [detect(name,spec,bool(set(spec['contexts'])&selected)) for name,spec in tool_registry().items()]

def download(url):
    try:
        with urllib.request.urlopen(url,timeout=45) as response:return response.read()
    except OSError:raise PrerequisiteError('vendor download failed; check network/DNS') from None

def run_installer(command):
    try:subprocess.run(command,check=True,stdout=sys.stderr)
    except (OSError,subprocess.CalledProcessError):raise PrerequisiteError('installer failed; inspect package-manager diagnostics') from None

def install(name,interactive=False,allow_install=False,allow_system=False,dry_run=False):
    specs=tool_registry()
    if name not in specs:raise PrerequisiteError('unknown tool')
    spec=specs[name];current=detect(name,spec,True)
    if current['status']=='ok':return {'name':name,'status':'unchanged'}
    if current['path']:
        raise PrerequisiteError(f'{name} is installed but unsupported; explicit operator-managed upgrade required')
    policy=json.loads((ROOT/'config/install-policy.json').read_text())
    if interactive:
        if not sys.stdin.isatty():raise PrerequisiteError('interactive installation requires a terminal')
        print(f'Install missing tool {name}? [y/N] ',file=sys.stderr,end='',flush=True)
        if input().lower()!='y':raise PrerequisiteError('installation declined')
    elif not allow_install and name not in policy['allow_tools']:
        raise PrerequisiteError(f'installation of {name} requires --allow-install or config/install-policy.json')
    info=platform_info()
    if not info['supported']:raise PrerequisiteError('unsupported platform')
    if dry_run:return {'name':name,'status':'would-install','platform':info}
    if name in ('terraform','alloy'):
        release=spec['version'];osname='darwin' if info['os']=='Darwin' else 'linux'
        filename=f'terraform_{release}_{osname}_{info["architecture"]}.zip' if name=='terraform' else f'alloy-{osname}-{info["architecture"]}.zip'
        base=f'https://releases.hashicorp.com/terraform/{release}/' if name=='terraform' else f'https://github.com/grafana/alloy/releases/download/v{release}/'
        hashes=download(base+(f'terraform_{release}_SHA256SUMS' if name=='terraform' else 'SHA256SUMS')).decode()
        expected=next((line.split()[0] for line in hashes.splitlines() if line.split()[-1].lstrip('*')==filename),None)
        if not expected:raise PrerequisiteError('vendor checksum unavailable')
        archive=download(base+filename)
        if hashlib.sha256(archive).hexdigest()!=expected:raise PrerequisiteError('vendor checksum mismatch')
        target=ROOT/'.runtime/tools/bin';target.mkdir(parents=True,exist_ok=True,mode=0o700)
        binary=zipfile.ZipFile(io.BytesIO(archive)).read('terraform' if name=='terraform' else f'alloy-{osname}-{info["architecture"]}')
        path=target/name;path.write_bytes(binary);path.chmod(0o700)
        os.environ['PATH']=str(target)+os.pathsep+os.environ.get('PATH',os.defpath)
    elif spec.get('installer')=='python-lock':
        if sys.prefix==sys.base_prefix:raise PrerequisiteError('activate a Python virtualenv before installing Ansible')
        run_installer([sys.executable,'-m','pip','install','-r',str(ROOT/'requirements.lock.txt')])
    elif info['package_manager']=='brew' and spec.get('brew'):
        run_installer(['brew','install',spec['brew']])
    elif info['package_manager']=='apt-get' and spec.get('apt'):
        if not (allow_system or policy.get('allow_system')):raise PrerequisiteError('system package installation requires --allow-system')
        prefix=[] if os.geteuid()==0 else ['sudo','-n']
        if prefix and not shutil.which('sudo'):raise PrerequisiteError('sudo not available; use an administrator')
        run_installer(prefix+['apt-get','update'])
        run_installer(prefix+['apt-get','install','-y',spec['apt']])
    else:raise PrerequisiteError(f'no approved installer for {name} on this platform; install from official vendor instructions; package managers are never bootstrapped')
    result=detect(name,spec,True)
    if result['status']!='ok':raise PrerequisiteError(f'{name} installation did not produce a supported executable; verify PATH/version')
    return result
