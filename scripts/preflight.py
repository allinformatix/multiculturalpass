"""Read-only provider checks and operation-specific shared-schema validation."""
import base64
import datetime
import hashlib
import hmac
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from environment import validate, ConfigError

class AuthenticationError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        return None

def secret_contexts(operation,ci=False):
    result={'state'}
    if operation in ('doctor','plan','apply','provision','deploy','destroy'):result.add('infra')
    if operation in ('doctor','deploy','configure','update'):result.add('server')
    if ci:result.add('ci')
    if ci and operation in ('deploy','configure','update','status','logs','backup','restore','destroy','observability'):result.add('ci_ssh')
    return result

def request(url,token=None,basic=None,method='GET',body=None,headers=None):
    head=headers or {}
    if token:head['Authorization']='Bearer '+token
    if basic:head['Authorization']='Basic '+base64.b64encode((basic[0]+':'+basic[1]).encode()).decode()
    req=urllib.request.Request(url,data=body,headers=head,method=method)
    try:
        with urllib.request.build_opener(NoRedirect).open(req,timeout=15) as response:
            raw=response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise AuthenticationError(f'provider request failed with HTTP {exc.code} ({urllib.parse.urlsplit(url).hostname}); check permission/scope') from None
    except (OSError,ValueError):raise AuthenticationError(f'provider unreachable or invalid response ({urllib.parse.urlsplit(url).hostname})') from None

def s3_check(data,cfg):
    """Signed read-only bucket HEAD; does not test create/delete permissions."""
    now=datetime.datetime.now(datetime.timezone.utc)
    date=now.strftime('%Y%m%d');stamp=now.strftime('%Y%m%dT%H%M%SZ')
    endpoint=urllib.parse.urlsplit(cfg['s3_endpoint']);path='/'+urllib.parse.quote(cfg['backup_bucket'],safe='')
    digest=hashlib.sha256(b'').hexdigest()
    canonical_headers=f'host:{endpoint.netloc}\nx-amz-content-sha256:{digest}\nx-amz-date:{stamp}\n'
    signed='host;x-amz-content-sha256;x-amz-date'
    canonical='HEAD\n'+path+'\n\n'+canonical_headers+'\n'+signed+'\n'+digest
    scope=date+'/'+cfg['s3_region']+'/s3/aws4_request'
    text='AWS4-HMAC-SHA256\n'+stamp+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
    key=('AWS4'+data['AWS_SECRET_ACCESS_KEY']).encode()
    for value in (date,cfg['s3_region'],'s3','aws4_request'):key=hmac.new(key,value.encode(),hashlib.sha256).digest()
    signature=hmac.new(key,text.encode(),hashlib.sha256).hexdigest()
    headers={'X-Amz-Date':stamp,'X-Amz-Content-Sha256':digest,'Authorization':'AWS4-HMAC-SHA256 Credential='+data['AWS_ACCESS_KEY_ID']+'/'+scope+', SignedHeaders='+signed+', Signature='+signature}
    try:
        with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(cfg['s3_endpoint']+path,headers=headers,method='HEAD'),timeout=15):
            return {'name':'s3','status':'ok','scope':'signed bucket HEAD; write permissions not proven'}
    except urllib.error.HTTPError as error:
        if error.code==404:return {'name':'s3','status':'warning','message':'bucket missing or hidden; credentials/write permissions not proven until provisioning'}
        raise AuthenticationError('S3 authentication or bucket-read permission failed') from None
    except OSError:raise AuthenticationError('S3 endpoint/DNS unreachable') from None

def cloud_checks(data,cfg,operation):
    checks=[]
    if 'infra' in secret_contexts(operation):
        request('https://api.hetzner.cloud/v1/servers?per_page=1',token=data['HCLOUD_TOKEN']);checks.append({'name':'hetzner','status':'ok','scope':'read verified; write permissions not proven'})
        result=request('https://api.cloudflare.com/client/v4/user/tokens/verify',token=data['CLOUDFLARE_API_TOKEN'])
        if not result.get('success') or result.get('result',{}).get('status')!='active':raise AuthenticationError('Cloudflare token is inactive')
        checks.append({'name':'cloudflare','status':'ok','scope':'token active; zone write permissions not proven'})
    if 'infra' in secret_contexts(operation):checks.append(s3_check(data,cfg))
    org=urllib.parse.quote(cfg['hcp_organization'],safe='');workspace=urllib.parse.quote(cfg['hcp_workspace'],safe='')
    request('https://app.terraform.io/api/v2/organizations/'+org,token=data['TF_TOKEN_app_terraform_io'])
    try:
        result=request(f'https://app.terraform.io/api/v2/organizations/{org}/workspaces/{workspace}',token=data['TF_TOKEN_app_terraform_io'])
        if result['data']['attributes']['execution-mode']!='local':raise AuthenticationError('HCP workspace must use local execution mode')
        checks.append({'name':'hcp-backend','status':'ok','scope':'workspace read verified; state write/lock still checked by Terraform'})
    except AuthenticationError as error:
        if operation in ('doctor','init') and 'HTTP 404' in str(error):checks.append({'name':'hcp-backend','status':'warning','message':'workspace missing or hidden; run init with bootstrap permissions'})
        else:raise
    return checks

def run(data,cfg,operation,ci=False,network=True):
    if ci and data.get('GITHUB_REPOSITORY')!=cfg['github_repository']:
        raise ConfigError('CI repository does not match configured github_repository')
    validate(data,secret_contexts(operation,ci),cfg)
    return cloud_checks(data,cfg,operation) if network else []
