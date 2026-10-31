#!/usr/bin/env python3
"""Fixture-only local E2E; no real configuration files are read."""
import http.cookiejar,json,os,subprocess,tempfile,time,urllib.request
from pathlib import Path
root=Path(__file__).resolve().parent.parent
values=dict(l.split('=',1) for l in (root/'.local/dev.env').read_text().splitlines())
base='http://localhost:8080';jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));csrf=''
def req(path,body=None):
 data=None if body is None else json.dumps(body).encode()
 r=urllib.request.Request(base+'/api/v1'+path,data=data,headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':csrf})
 with opener.open(r) as res:return json.load(res)
csrf=req('/auth/login',{'email':values['ADMIN_EMAIL'],'password':values['ADMIN_PASSWORD']})['csrf_token']
org=req('/organizations')['items'][0]['id'];project=req('/organizations/'+org+'/projects')['items'][0]['id'];env=req('/projects/'+project+'/environments')['items'][0]['id']
server=req('/environments/'+env+'/servers',{'display_name':'laboratorio-local'})['id'];creds=req('/servers/'+server+'/agents',{})
token=root/'.local/agent.token';token.write_text(creds['token']);token.chmod(0o600)
fixture=Path(tempfile.mkdtemp(prefix='configsentinel-lab-'))/'demo.conf';fixture.write_text('synthetic=true\nrevision=1\n')
config={'agent':{'server_url':'http://127.0.0.1:8080/api/v1','agent_id':creds['agent_id'],'token_file':str(token),'queue_db':str(root/'.local/demo-queue.sqlite'),'interval_seconds':5,'send_batch_size':100,'allow_insecure_loopback':True},'monitoring':{'files':[{'path':str(fixture),'alias':'laboratorio-demo','hash_only':True}]}}
config_file=root/'.local/agent.yaml';config_file.write_text(json.dumps(config));config_file.chmod(0o600)
def cycle():subprocess.run([str(root/'bin/configsentinel-agent'),'-config',str(config_file),'-once'],check=True)
cycle();fixture.write_text('synthetic=true\nrevision=2\n');cycle();fixture.unlink();cycle();fixture.write_text('synthetic=true\nrevision=3\n');cycle()
events=req('/events?server_id='+server)['items'];assert {e['kind'] for e in events}>={'baseline','modified','deleted','restored'}
req('/events/'+next(e for e in events if e['kind']=='modified')['id']+'/acknowledgements',{'comment':'Alteração sintética de laboratório validada no fluxo ponta a ponta.'})
(root/'.local/demo-state.json').write_text(json.dumps({'server_id':server,'agent_id':creds['agent_id'],'token_id':creds['token_id'],'fixture':str(fixture)}))
print('Fixture E2E: baseline, modified, deleted, restored, acknowledgement confirmed; no file content sent.')
