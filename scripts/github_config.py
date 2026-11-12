"""GitHub metadata checks and explicit, stdin-only environment synchronization."""
import json
import re
import subprocess
from environment import ROOT, registry, ConfigError, applicable

class GitHubError(ValueError):
    pass

def api(path):
    proc=subprocess.run(['gh','api','--paginate',path],capture_output=True,text=True,check=False)
    if proc.returncode:
        code=next((code for code in ('401','403','404') if code in proc.stderr),'unknown')
        raise GitHubError(f'GitHub API unavailable or insufficient permissions (HTTP {code})')
    try:
        # gh --paginate emits adjacent JSON objects; collect all pages safely.
        decoder=json.JSONDecoder();text=proc.stdout.strip();pages=[]
        while text:
            page,end=decoder.raw_decode(text);pages.append(page);text=text[end:].lstrip()
        return pages
    except (ValueError,TypeError):raise GitHubError('invalid GitHub API response') from None

def items(path,key):return [item for page in api(path) for item in page.get(key,[])]

def expected(data,contexts,config,kind):
    required=[]
    for name,spec in registry().items():
        if spec.get('alias_for') or spec['github']!=kind or not spec['sync']:continue
        is_required=bool(set(spec['required_for'])&set(contexts))
        if config['observability_enabled'] and 'observability' in spec['required_for']:is_required=True
        if is_required and applicable(spec,config):required.append((name,spec.get('github_name',name)))
    return required

def inventory(repo,env,kind):
    plural='secrets' if kind=='secret' else 'variables'
    paths=[('environment',f'repos/{repo}/environments/{env}/{plural}'),('repository',f'repos/{repo}/actions/{plural}'),('organization',f'orgs/{repo.split("/")[0]}/actions/{plural}')]
    found={};unknown=[]
    for scope,path in paths:
        try:
            for entry in items(path,plural):
                if scope=='organization':
                    visibility=entry.get('visibility')
                    if visibility=='selected':
                        selected=items(path+'/'+entry['name']+'/repositories','repositories')
                        if not any(r['full_name']==repo for r in selected):continue
                    elif visibility=='private':
                        if not api('repos/'+repo)[0].get('private'):continue
                found.setdefault(entry['name'],{'scope':scope,'value':entry.get('value')})
        except GitHubError:unknown.append(scope)
    return found,unknown

def check(data,config,kind,contexts):
    repo=config['github_repository'];env=config['environment']
    api(f'repos/{repo}/environments/{env}')
    found,unknown=inventory(repo,env,kind)
    result=[]
    for local,name in expected(data,contexts,config,kind):
        entry=found.get(name)
        status='present-value-unverifiable' if entry and kind=='secret' else 'present' if entry else 'unknown-permissions' if unknown else 'missing'
        result.append({'name':name,'kind':kind,'status':status,'scope':entry['scope'] if entry else None,'unreadable_scopes':unknown})
    return {'checks':result,'unreadable_scopes':unknown}

def sync(data,config,overwrite=False,confirmation='',dry_run=False):
    repo=config['github_repository'];env=config['environment']
    if env=='prd' and confirmation!=config['name']+':sync-github':raise ConfigError('prd sync requires --confirm PROJECT-prd:sync-github')
    api(f'repos/{repo}/environments/{env}')
    report=[]
    for kind in ('secret','variable'):
        existing,unknown=inventory(repo,env,kind)
        for local,spec in registry().items():
            if not spec['sync'] or spec['github']!=kind or spec.get('alias_for') or not data.get(local):continue
            name=spec.get('github_name',local)
            # Even optional nonempty values must not overwrite inherited/repository credentials silently.
            if name in existing and not overwrite:
                report.append({'name':name,'status':'retained'});continue
            if name not in existing and unknown:
                report.append({'name':name,'status':'blocked-unreadable-scope'});continue
            if dry_run:report.append({'name':name,'status':'would-write'});continue
            command=['gh','secret' if kind=='secret' else 'variable','set',name,'--repo',repo,'--env',env]
            # gh encrypts secret values using the environment public key; input never becomes argv.
            proc=subprocess.run(command,input=data[local],text=True,capture_output=True,check=False)
            if proc.returncode:raise GitHubError(f'could not synchronize {name}; verify permissions')
            report.append({'name':name,'status':'written'})
    return report

def audit_workflows():
    known={(spec.get('github_name',key),spec['github']) for key,spec in registry().items()}
    missing=[]
    for path in (ROOT/'.github').rglob('*.yml'):
        for kind,name in re.findall(r'\b(secrets|vars)\.([A-Za-z_][A-Za-z0-9_]*)',path.read_text()):
            if name=='GITHUB_TOKEN':continue
            if (name,'secret' if kind=='secrets' else 'variable') not in known:missing.append(path.name+':'+name)
    if missing:raise ConfigError('workflow references absent from registry: '+', '.join(sorted(set(missing))))
    return {'workflow_registry':'ok'}
