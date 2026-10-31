#!/usr/bin/env python3
"""Provision an authorized synthetic laboratory; secrets are written only to ignored files."""
import http.cookiejar,json,os,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent.parent
values=dict(l.split('=',1) for l in (root/'.local/homolog.env').read_text().splitlines())
base=values['PUBLIC_URL'];jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));csrf=''
def req(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 r=urllib.request.Request(base+'/api/v1'+path,data=data,headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':csrf})
 with opener.open(r,timeout=30) as res:return json.load(res)
csrf=req('/auth/login',{'email':values['ADMIN_EMAIL'],'password':values['ADMIN_PASSWORD']})['csrf_token']
org=req('/organizations')['items'][0]['id'];project=req('/organizations/'+org+'/projects')['items'][0]['id'];env=req('/projects/'+project+'/environments')['items'][0]['id']
server=req('/environments/'+env+'/servers',{'display_name':'frank-note2-laboratorio'})['id'];creds=req('/servers/'+server+'/agents',{})
install=root/'.local/lab-install';install.mkdir(exist_ok=True)
(install/'agent.token').write_text(creds['token']);(install/'agent.token').chmod(0o600)
config={'agent':{'server_url':base+'/api/v1','agent_id':creds['agent_id'],'token_file':'/config/agent.token','queue_db':'/state/events.sqlite','interval_seconds':5,'send_batch_size':100},'monitoring':{'files':[{'path':'/fixtures/demo.conf','alias':'laboratorio-demo','hash_only':True}]}}
(install/'agent.yaml').write_text(json.dumps(config,indent=2));(install/'demo.conf').write_text('synthetic=true\nrevision=1\n')
(root/'.local/homolog-agent.json').write_text(json.dumps({'server_id':server,**creds}));(root/'.local/homolog-agent.json').chmod(0o600)
print('Synthetic laboratory identity provisioned; credential stored in .local/lab-install/agent.token (0600).')
