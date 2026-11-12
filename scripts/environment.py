"""Typed environment registry and strict, nonexecuting dotenv parser."""
import json
import os
from pathlib import Path
import re
import shlex
import stat
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
class ConfigError(ValueError):
    pass

def registry():
    return json.loads((ROOT/'config/variables.json').read_text())['variables']

def parse(path):
    if not path.exists():
        raise ConfigError(f'Missing environment configuration: {path.name}; run ./ops.sh env init --env {path.suffix[1:]}')
    if path.is_symlink() or not path.is_file():
        raise ConfigError('environment must be a regular non-symlink file')
    if stat.S_IMODE(path.stat().st_mode)&0o077:
        raise ConfigError(f'{path.name} must have permissions 0600')
    result={}
    for number,line in enumerate(path.read_text().splitlines(),1):
        line=line.strip()
        if not line or line.startswith('#'):continue
        match=re.fullmatch(r'([A-Z_][A-Za-z0-9_]*)=(.*)',line)
        if not match:raise ConfigError(f'invalid dotenv syntax on line {number}')
        key,value=match.groups()
        if key in result:raise ConfigError(f'duplicate dotenv key: {key}')
        if any(c in value for c in ('`','$','\x00')):
            raise ConfigError(f'expansion/execution syntax forbidden for {key}')
        if value.startswith(('"',"'")):
            if len(value)<2 or value[-1]!=value[0] or '\\' in value:
                raise ConfigError(f'invalid quoted dotenv value: {key}')
            value=value[1:-1]
        elif any(c.isspace() for c in value) or '#' in value or any(c in value for c in (';', '|','<','>','\\')):
            raise ConfigError(f'quote whitespace and special characters for {key}')
        if key not in registry():raise ConfigError(f'unknown dotenv variable: {key}')
        result[key]=value
    return result

def values(env, require_file=False, process=None):
    specs=registry()
    data={k:str(v['default']).lower() if isinstance(v['default'],bool) else str(v['default']) for k,v in specs.items()}
    process=os.environ if process is None else process
    if env and process.get('CI')!='true':
        path=ROOT/f'.env.{env}'
        if path.exists() or require_file:data.update(parse(path))
    data.update({k:process[k] for k in specs if process.get(k) not in (None,'')})
    for key,spec in specs.items():
        target=spec.get('alias_for')
        if target and data[key]:
            if data[target] and data[target]!=str(specs[target]['default']) and data[target]!=data[key]:
                raise ConfigError(f'conflicting aliases: {key}/{target}')
            data[target]=data[key]
    if env:
        if data['ENVIRONMENT'] and data['ENVIRONMENT']!=env:raise ConfigError('ENVIRONMENT does not match --env')
        data['ENVIRONMENT']=env
    return data

def overlay(config,env,process=None):
    process=os.environ if process is None else process
    data=values(env,process=process)
    # Defaults already live in JSON; only explicit dotenv/process values override JSON.
    explicit={}
    if env and process.get('CI')!='true' and (ROOT/f'.env.{env}').exists():explicit.update(parse(ROOT/f'.env.{env}'))
    explicit.update({k:process[k] for k in registry() if process.get(k) not in (None,'')})
    for key in explicit:
        target=registry()[key].get('alias_for',key)
        spec=registry()[target]
        if data[target] and spec.get('config_key'):
            config[spec['config_key']]=convert(target,data[target],spec)
    if data.get('SSH_PUBLIC_KEY_PATH'):
        key_path=Path(data['SSH_PUBLIC_KEY_PATH']).expanduser()
        if not key_path.is_file():raise ConfigError('SSH_PUBLIC_KEY_PATH does not exist')
        config['ssh_public_key']=key_path.read_text().strip()
    return config

def convert(key,value,spec):
    if spec['type']=='boolean':
        if value not in ('true','false'):raise ConfigError(f'{key} must be true or false')
        return value=='true'
    if spec['type']=='integer':
        if not re.fullmatch(r'[0-9]+',value):raise ConfigError(f'{key} must be an integer')
        return int(value)
    return value

def effective(env,config,require_file=False):
    data=values(env,require_file)
    for key,spec in registry().items():
        mapped=spec.get('config_key')
        if mapped in config:
            value=config[mapped]
            data[key]=str(value).lower() if isinstance(value,bool) else str(value)
    if data['SSH_PRIVATE_KEY_PATH']:
        key_path=Path(data['SSH_PRIVATE_KEY_PATH']).expanduser()
        if not key_path.is_file() or key_path.stat().st_mode&0o077:raise ConfigError('SSH_PRIVATE_KEY_PATH missing or permissions must be 0600')
        data['SSH_PRIVATE_KEY']=key_path.read_text()
    if data['SSH_KNOWN_HOSTS_PATH']:
        key_path=Path(data['SSH_KNOWN_HOSTS_PATH']).expanduser()
        if not key_path.is_file():raise ConfigError('SSH_KNOWN_HOSTS_PATH missing')
        data['SSH_KNOWN_HOSTS']=key_path.read_text()
    expected={'ENVIRONMENT':env,'PROJECT_NAME':config['name'],'LOG_TENANT':config['tenant_id'] or config['slug'], 'TENANT_ID':config['tenant_id'] or config['slug'],'LOG_STAGE':env,'LOG_PROJECT':config['slug'],'LOG_APPLICATION':'odoo','LOG_PROVIDER':config['cloud_provider'],'LOG_REGION':config['region'],'S3_BUCKET':config['backup_bucket']}
    for key,value in expected.items():
        if data[key] and data[key]!=str(registry()[key]['default']) and data[key]!=value:
            raise ConfigError(f'{key} conflicts with derived project/environment identity')
        data[key]=value
    return data

def applicable(spec,config):
    defaults=json.loads((ROOT/'config/defaults.json').read_text())
    return all(config.get(key,defaults.get(key))==value for key,value in spec.get('required_when',{}).items())

def validate_loki_url(value):
    try:
        url=urlsplit(value)
        valid=url.scheme=='https' and url.hostname and re.fullmatch(r'logs[-a-z0-9.]*\.grafana\.net',url.hostname) and url.path=='/loki/api/v1/push' and not url.query and not url.fragment and not url.username and not url.password and url.port in (None,443)
    except ValueError:valid=False
    if not valid:raise ConfigError('GRAFANA_CLOUD_LOKI_URL must be a Grafana Cloud HTTPS Loki push endpoint without credentials/query')

def validate(data,contexts,config):
    errors=[]
    if config.get('observability_enabled'):contexts=set(contexts)|{'observability'}
    for key,spec in registry().items():
        if spec.get('alias_for'):continue
        value=data.get(key,'')
        if applicable(spec,config) and set(spec['required_for'])&set(contexts) and not value:errors.append(f'missing {key}')
        if not value:continue
        try:convert(key,value,spec)
        except ConfigError as error:errors.append(str(error))
        if spec.get('secret') and key not in ('SSH_PRIVATE_KEY_PATH',) and len(value)<16:errors.append(f'{key} is too short')
        if spec.get('pattern') and not re.fullmatch(spec['pattern'],value):errors.append(f'invalid {key} format')
    if config.get('observability_enabled'):
        try:validate_loki_url(data['GRAFANA_CLOUD_LOKI_URL'])
        except ConfigError as error:errors.append(str(error))
    if errors:raise ConfigError('; '.join(errors))

def example(env=None,config=None):
    lines=['# Generated from config/variables.json; no expansion, multiline values or shell code.']
    for key,spec in registry().items():
        if spec.get('alias_for'):lines.append(f'# Compatibility alias for {spec["alias_for"]}')
        else:lines.append(f'# {spec["type"]}; {"secret" if spec["secret"] else "nonsecret"}; required: {",".join(spec["required_for"]) or "optional"}')
        value=spec['default']
        if env and key=='ENVIRONMENT':value=env
        if config and spec.get('config_key') in config:value=config[spec['config_key']]
        if isinstance(value,bool):value=str(value).lower()
        value=str(value)
        if value and any(c.isspace() for c in value):value="'"+value+"'"
        lines.append(key+'='+value)
    return '\n'.join(lines)+'\n'

def initialize(env,confirmation='',dry_run=False):
    path=ROOT/f'.env.{env}'
    if path.exists():
        if confirmation!=f'{env}:overwrite-env':raise ConfigError('existing environment retained; exact --confirm ENV:overwrite-env is required')
        if path.is_symlink():raise ConfigError('refusing to overwrite a symlink')
    if dry_run:return {'environment':env,'path':path.name,'status':'would-create'}
    # Structural defaults, intentionally empty credentials: env validate explains what is still needed.
    from config import load
    try:cfg=load(env,strict=False)
    except (ValueError,OSError,KeyError):cfg=None
    flags=os.O_WRONLY|os.O_CREAT|(os.O_TRUNC if path.exists() else os.O_EXCL)
    fd=os.open(path,flags|getattr(os,"O_NOFOLLOW",0),0o600)
    with os.fdopen(fd,'w') as stream:stream.write(example(env,cfg))
    path.chmod(0o600)
    return {'environment':env,'path':path.name,'status':'created','credentials':'empty; operator must supply values'}
