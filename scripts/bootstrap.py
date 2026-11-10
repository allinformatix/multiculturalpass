#!/usr/bin/env python3
"""Idempotent HCP API bootstrap. No local Terraform state or cloud provisioning."""
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from config import load

def request(method,path,payload=None,missing=False):
    token=os.environ.get('TF_TOKEN_app_terraform_io')
    if not token: raise ValueError('TF_TOKEN_app_terraform_io is required')
    req=urllib.request.Request('https://app.terraform.io/api/v2/'+path,data=json.dumps(payload).encode() if payload else None,method=method,headers={'Authorization':'Bearer '+token,'Content-Type':'application/vnd.api+json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    except urllib.error.HTTPError as exc:
        if missing and exc.code==404:return None
        raise ValueError(f'HCP API {method} failed with HTTP {exc.code}; verify permissions and project configuration') from None

def bootstrap(cfg):
    org=urllib.parse.quote(cfg['hcp_organization'],safe='')
    project_id=None
    # Optional explicit project name allows reuse when project creation is not permitted.
    path=f'organizations/{org}/projects?page%5Bsize%5D=100'
    while path:
        page=request('GET',path)
        for item in page['data']:
            if item['attributes']['name']==cfg['hcp_project']:project_id=item['id']
        next_url=page.get('links',{}).get('next')
        path=next_url.split('/api/v2/',1)[1] if next_url else None
    if not project_id:
        project_id=request('POST',f'organizations/{org}/projects',{'data':{'type':'projects','attributes':{'name':cfg['hcp_project']}}})['data']['id']
    workspace_path=f"organizations/{org}/workspaces/{urllib.parse.quote(cfg['hcp_workspace'],safe='')}"
    workspace=request('GET',workspace_path,missing=True)
    payload={'data':{'type':'workspaces','attributes':{'name':cfg['hcp_workspace'],'execution-mode':'local','auto-apply':False},'relationships':{'project':{'data':{'type':'projects','id':project_id}}}}}
    if workspace:
        if workspace['data']['relationships']['project']['data']['id']!=project_id:
            raise ValueError('workspace already belongs to a different project; refusing to move it')
        if workspace['data']['attributes']['execution-mode']!='local':
            raise ValueError('existing workspace must use local execution; refusing implicit change')
    else:request('POST',f'organizations/{org}/workspaces',payload)
    # Does not invent reviewer identities. Production mutations fail closed until a reviewer exists.
    repo=cfg['github_repository']; env=cfg['environment']
    proc=subprocess.run(['gh','api',f'repos/{repo}/environments/{env}'],capture_output=True)
    if proc.returncode:
        if b'404' not in proc.stderr:
            raise ValueError('cannot read GitHub environment; refusing to overwrite protection')
        proc=subprocess.run(['gh','api','--method','PUT',f'repos/{repo}/environments/{env}','--input','-'],input=b'{}',check=True,capture_output=True)
    result=json.loads(proc.stdout)
    if env=='prd' and not any(rule.get('type')=='required_reviewers' and rule.get('reviewers') for rule in result.get('protection_rules',[])):
        raise ValueError('configure required reviewers for GitHub environment prd, then rerun init; see docs/security.md')

if __name__=='__main__':
    try:bootstrap(load(sys.argv[1]))
    except (ValueError,subprocess.CalledProcessError) as error:sys.exit(str(error))
