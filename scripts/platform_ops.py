#!/usr/bin/env python3
"""Management commands of ops.sh; the Bash deployment orchestrator remains authoritative."""
import argparse
import json
import os
import subprocess
import sys
from config import load
from environment import ROOT, ConfigError, effective, example, initialize, registry, validate
import prerequisites as tools
import github_config as github
import preflight


def emit(value,machine=False):
    if machine:print(json.dumps(value,sort_keys=True));return
    if isinstance(value,dict) and 'sections' in value:
        print('Odoo All-in-One Infrastructure Doctor')
        for section,entries in value['sections'].items():
            print('\n'+section.upper())
            for entry in entries:print(f'[{entry.get("status","info").upper()}] {entry.get("name","")} {entry.get("message","")}')
        print(f'\nRESULT: {value["errors"]} errors, {value["warnings"]} warnings')
    else:print(json.dumps(value,indent=2,sort_keys=True))

def configuration(env,required=True):
    cfg=load(env)
    return cfg,effective(env,cfg,require_file=required and os.environ.get('CI')!='true')

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['doctor','prerequisites','env','github','preflight'])
    parser.add_argument('action',nargs='?',default='')
    parser.add_argument('detail',nargs='?',default='')
    parser.add_argument('--env',choices=['dev','stg','prd'])
    parser.add_argument('--env2',choices=['dev','stg','prd'])
    for flag in ['fix','json','interactive','non-interactive','allow-install','allow-system','dry-run','redact','overwrite']:
        parser.add_argument('--'+flag,action='store_true',dest=flag.replace('-','_'))
    parser.add_argument('--confirm',default='')
    parser.add_argument('--operation',default='doctor')
    args=parser.parse_args(argv)
    if args.interactive and args.non_interactive:raise ConfigError('choose interactive or non-interactive')
    if args.command=='prerequisites':
        reports=tools.inspect(args.operation)
        if args.action=='list':emit({'platform':tools.platform_info(),'tools':reports},args.json);return 0
        if args.action!='install':raise ConfigError('use prerequisites list|install')
        result=[]
        for report in reports:
            if report['selected'] and report['status']!='ok':result.append(tools.install(report['name'],args.interactive,args.allow_install,args.allow_system,args.dry_run))
        emit(result,args.json);return 0
    if args.command=='env':
        if not args.env:raise ConfigError('--env is required')
        if args.action=='init':emit(initialize(args.env,args.confirm,args.dry_run),args.json);return 0
        cfg,data=configuration(args.env)
        if args.action=='validate':validate(data,preflight.secret_contexts('doctor'),cfg);emit({'environment':args.env,'status':'valid'},args.json)
        elif args.action=='show':emit({k:('[REDACTED]' if spec['secret'] and data[k] else data[k]) for k,spec in registry().items()},args.json)
        elif args.action=='diff':
            if not args.env2:raise ConfigError('--env2 is required')
            _,other=configuration(args.env2)
            emit({key:({'changed':True,'values':'[REDACTED]'} if registry()[key]['secret'] else {'left':data[key],'right':other[key]}) for key in data if data[key]!=other[key]},args.json)
        else:raise ConfigError('use env init|validate|show|diff')
        return 0
    if args.command=='doctor':
        sections={'platform':[],'tools':[],'environment':[],'github':[],'observability':[],'providers':[]}
        info=tools.platform_info();sections['platform']=[{'name':f'{info["distribution"]} {info["architecture"]}','status':'ok' if info['supported'] else 'error','message':f'package manager: {info["package_manager"]}; uid: {info["uid"]}'}]
        reports=tools.inspect('doctor')
        if args.fix:
            for report in reports:
                if report['selected'] and report['status']!='ok':
                    try:tools.install(report['name'],args.interactive,args.allow_install,args.allow_system,args.dry_run)
                    except tools.PrerequisiteError as error:sections['tools'].append({'name':report['name'],'status':'error','message':str(error)})
            reports=tools.inspect('doctor')
        sections['tools']+=reports
        config_error=False;auth_error=False
        if args.env:
            try:
                cfg,data=configuration(args.env);validate(data,preflight.secret_contexts('doctor'),cfg)
                sections['environment'].append({'name':args.env,'status':'ok'})
                sections['observability'].append({'name':'grafana-cloud','status':'warning' if cfg['observability_enabled'] else 'skipped','message':'enabled; collector deployment/delivery not verified' if cfg['observability_enabled'] else 'disabled'})
                if not args.dry_run:
                    try:
                        sections['providers']=preflight.cloud_checks(data,cfg,'doctor')
                        if any(r['name']=='gh' and r['status']=='ok' for r in reports):
                            for kind in ('secret','variable'):sections['github']+=github.check(data,cfg,kind,preflight.secret_contexts('doctor',True))['checks']
                    except (preflight.AuthenticationError,github.GitHubError) as error:
                        auth_error=True;sections['providers'].append({'name':'authentication','status':'error','message':str(error)})
            except (ValueError,OSError,KeyError) as error:
                config_error=True;sections['environment'].append({'name':args.env,'status':'error','message':str(error)})
        entries=[item for values in sections.values() for item in values]
        auth_error=auth_error or any(item['status']=='unknown-permissions' for item in sections['github'])
        config_error=config_error or any(item['status']=='missing' for item in sections['github'])
        errors=sum(item['status'] in ('error','missing','unsupported','unknown-permissions') for item in entries)
        warnings=sum(item['status']=='warning' for item in entries)
        emit({'sections':sections,'errors':errors,'warnings':warnings},args.json)
        return 4 if auth_error else 3 if config_error else 2 if errors else 0
    if not args.env and not (args.command=='github' and args.action=='environments' and args.detail=='list'):raise ConfigError('--env is required')
    if args.command=='github' and args.action=='environments' and args.detail=='list':
        project=json.loads((ROOT/'config/project.json').read_text())
        emit(github.items('repos/'+project['github_repository']+'/environments','environments'),args.json);return 0
    cfg,data=configuration(args.env)
    if args.command=='preflight':
        selected=tools.inspect(args.operation)
        failures=[item['name'] for item in selected if item['selected'] and item['status']!='ok']
        if failures:raise tools.PrerequisiteError('missing/unsupported tools: '+', '.join(failures))
        emit(preflight.run(data,cfg,args.operation,os.environ.get('CI')=='true',not args.dry_run),args.json);return 0
    if args.command=='github':
        if tools.detect('gh',tools.tool_registry()['gh'],True)['status']!='ok':raise tools.PrerequisiteError('GitHub CLI missing or unsupported; run prerequisites install')
        github.audit_workflows()
        if args.action=='sync':
            # Construct only the two explicitly synchronized JSON variables; never embed secrets.
            data['PROJECT_CONFIG']=(ROOT/'config/project.json').read_text()
            allowed=json.loads((ROOT/'config/schema.json').read_text())['properties']
            data['ENVIRONMENT_CONFIG']=json.dumps({key:value for key,value in cfg.items() if key in allowed})
            validate(data,preflight.secret_contexts('doctor',True)-{'ci_ssh'},cfg)
            emit(github.sync(data,cfg,args.overwrite,args.confirm,args.dry_run),args.json);return 0
        if args.action not in ('doctor','secrets','vars') or args.detail not in ('','check'):raise ConfigError('use github doctor|sync|secrets check|vars check|environments list')
        results=[]
        for kind in (('secret','variable') if args.action=='doctor' else ('secret',) if args.action=='secrets' else ('variable',)):
            results+=github.check(data,cfg,kind,preflight.secret_contexts('doctor',True))['checks']
        emit(results,args.json)
        return 4 if any(r['status']=='unknown-permissions' for r in results) else 3 if any(r['status']=='missing' for r in results) else 0
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (ConfigError,ValueError,OSError,KeyError) as error:
        code=4 if isinstance(error,(preflight.AuthenticationError,github.GitHubError)) else 2 if isinstance(error,tools.PrerequisiteError) else 3
        # Values never included by validation/errors; external stderr is captured by adapters.
        if '--json' in sys.argv:print(json.dumps({'status':'error','message':str(error),'exit_code':code}))
        else:print('error: '+str(error),file=sys.stderr)
        sys.exit(code)
