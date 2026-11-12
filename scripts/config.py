#!/usr/bin/env python3
"""Merge only known, nonsecret configuration. Never execute configuration as code."""
import ipaddress
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def load(env, strict=True):
    if env not in ('dev', 'stg', 'prd'):
        raise ValueError('environment must be dev, stg or prd')
    config = {}
    for path in (ROOT/'config/defaults.json', ROOT/'config/project.json', ROOT/f'config/environments/{env}.json'):
        if path.name == 'project.json' and not path.exists():
            raise ValueError('copy config/project.example.json to config/project.json first')
        config.update(json.loads(path.read_text()))
    from environment import overlay
    config = overlay(config, env)
    config.setdefault("alloy_version",json.loads((ROOT/"config/tools.json").read_text())["tools"]["alloy"]["version"]+"-1")
    schema = json.loads((ROOT/'config/schema.json').read_text())
    try:
        import jsonschema
        try:
            jsonschema.validate(config, schema)
        except jsonschema.ValidationError as exc:
            raise ValueError('schema validation failed at '+'.'.join(str(p) for p in exc.absolute_path)+' ('+str(exc.validator)+')') from None
    except ImportError as exc:
        raise ValueError('install requirements.txt (jsonschema required)') from exc
    for key in ('slug', 'database', 'ssh_user', 'hcp_organization'):
        if not re.fullmatch(r'[a-z][a-z0-9_-]{1,39}', config[key]):
            raise ValueError(f'invalid {key}')
    if config['ssh_user'] in ('root','odoo','postgres') or config['database'] in ('postgres','template0','template1'):
        raise ValueError('reserved administrator or database name')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,25}', config['slug']):
        raise ValueError('invalid slug')
    if not re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}', config['hostname']):
        raise ValueError('invalid hostname')
    for key in ('ssh_cidrs', 'web_cidrs'):
        for cidr in config[key]:
            net = ipaddress.ip_network(cidr, strict=True)
            if key == 'ssh_cidrs' and net.prefixlen == 0:
                raise ValueError('SSH from the entire internet is forbidden')
    for key in ('odoo_image', 'postgres_image'):
        if not re.fullmatch(r'[a-zA-Z0-9./_:@-]+', config[key]) or ':latest' in config[key]:
            raise ValueError(f'explicit safe image tag/digest required: {key}')
    if not re.fullmatch(r'odoo:18\.0(?:@sha256:[a-f0-9]{64})?', config['odoo_image']):
        raise ValueError('only Odoo 18 supported; major migrations require a separate migration project')
    if not re.fullmatch(r'postgres:16\.\d+(?:@sha256:[a-f0-9]{64})?', config['postgres_image']):
        raise ValueError('only PostgreSQL 16 supported; major migrations are not updates')
    if not re.fullmatch(r'https://[a-z0-9.-]+\.your-objectstorage\.com', config['s3_endpoint']):
        raise ValueError('expected a Hetzner HTTPS S3 endpoint')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', config['acme_email']):
        raise ValueError('invalid ACME email')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', config['github_repository']):
        raise ValueError('invalid GitHub repository')
    if not re.fullmatch(r'ssh-(ed25519|rsa) [A-Za-z0-9+/=]+(?: [^\r\n]+)?', config['ssh_public_key']):
        raise ValueError('invalid SSH public key')
    if strict:
        for key in ('hostname','cloudflare_zone_id','hcp_organization','ssh_public_key'):
            if 'REPLACE' in config[key] or 'example.com' in config[key] or config[key] == 'your-organization':
                raise ValueError(f'configure {key} before running')
        if not re.fullmatch(r'[a-f0-9]{32}', config['cloudflare_zone_id']):
            raise ValueError('Cloudflare zone ID must be 32 lowercase hex characters')
        for cidr in config['ssh_cidrs']:
            if ipaddress.ip_network(cidr).network_address.is_reserved or cidr.startswith('192.0.2.'):
                raise ValueError('replace documentation SSH CIDR with actual administrator/runner egress')
    if config['cloudflare_proxied'] and not config['manage_cache_rules'] and not config['external_cache_bypass_confirmed']:
        raise ValueError('proxied Odoo requires owned cache bypass rules or explicit external_cache_bypass_confirmed')
    if config['manage_cache_rules'] and config['hostname'] not in config['cache_hostnames']:
        raise ValueError('cache_hostnames must contain this hostname when managing cache rules')
    config['cloudflare_cidrs'] = json.loads((ROOT/'config/cloudflare-ips.json').read_text())
    if config['cloudflare_proxied'] and any(cidr not in config['cloudflare_cidrs'] for cidr in config['web_cidrs']):
        raise ValueError('proxied origin must restrict web_cidrs to published Cloudflare networks')
    config['environment'] = env
    config.setdefault('hcp_project', f"{config['slug']}-{env}")
    config.setdefault('hcp_workspace', f"{config['slug']}-{env}")
    for key in ('hcp_project','hcp_workspace'):
        if not re.fullmatch(r'[a-zA-Z0-9_-]{3,40}',config[key]):
            raise ValueError(f'invalid {key}')
    # Validate isolation before even initializing a backend, including explicit overrides.
    for other in ('dev', 'stg', 'prd'):
        if other == env:
            continue
        candidate = {}
        for path in (ROOT/'config/defaults.json', ROOT/'config/project.json', ROOT/f'config/environments/{other}.json'):
            candidate.update(json.loads(path.read_text()))
        candidate = overlay(candidate, other, process={'CI':os.environ.get('CI','false')})
        workspace = candidate.get('hcp_workspace', f"{candidate['slug']}-{other}")
        if (candidate['hcp_organization'], workspace) == (config['hcp_organization'], config['hcp_workspace']):
            raise ValueError('environments must not share an HCP workspace')
        if candidate['hostname'] == config['hostname']:
            raise ValueError('environments must use different hostnames')
        if candidate['cloudflare_zone_id'] == config['cloudflare_zone_id']:
            for key in ('manage_zone_settings', 'manage_cache_rules'):
                if candidate[key] and config[key]:
                    raise ValueError(f'only one environment may own {key} for a shared zone')
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:ZoneInfo(config['server_timezone'])
    except (ValueError,ZoneInfoNotFoundError):raise ValueError('invalid SERVER_TIMEZONE') from None
    config['tenant_id'] = config['tenant_id'] or config['slug']
    if config['observability_enabled']:
        from prerequisites import version, tool_registry
        alloy=tool_registry()['alloy']
        if not (version(alloy['minimum']) <= version(config['alloy_version']) < version(alloy['maximum'])):
            raise ValueError('Alloy version is outside the supported registry range')
        from environment import validate_loki_url
        validate_loki_url(config['loki_url'])
    config['name'] = f"{config['slug']}-{env}"
    config['backup_bucket'] = f"{config['name']}-backups"
    return config

def render(config):
    target = ROOT/'.runtime'/config['environment']
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    (target/'config.json').write_text(json.dumps(config,indent=2))
    tfkeys = ['name','environment','hostname','cloudflare_zone_id','ssh_public_key','ssh_cidrs','web_cidrs','server_type','region','image','backup_bucket','cloudflare_proxied','manage_zone_settings','manage_cache_rules','s3_endpoint','s3_region','cache_hostnames']
    (target/'terraform.tfvars.json').write_text(json.dumps({k:config[k] for k in tfkeys},indent=2))
    (target/'backend.hcl').write_text('organization = '+json.dumps(config['hcp_organization'])+'\nworkspaces { name = '+json.dumps(config['hcp_workspace'])+' }\n')
    return target

if __name__ == '__main__':
    try:
        cfg=load(sys.argv[1])
        if len(sys.argv)>2 and sys.argv[2]=='get':
            value=cfg[sys.argv[3]]
            print(json.dumps(value) if isinstance(value,(list,dict,bool)) else value)
        else:
            print(render(cfg))
    except (ValueError, KeyError, OSError) as error:
        sys.exit('configuration error: '+str(error))
