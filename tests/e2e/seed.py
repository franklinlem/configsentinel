"""Synthetic API fixtures for browser CI; actual agent is tested separately."""
import os,datetime,hashlib,http.cookiejar,json,urllib.request,uuid
from pathlib import Path
values=dict(l.split('=',1) for l in Path(os.environ.get('E2E_ENV_FILE','.local/dev.env')).read_text().splitlines());base=os.environ.get('E2E_BASE_URL','http://localhost:8080');csrf=''
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(path,body=None,token=None):
 headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':csrf}
 if token:headers['Authorization']='Bearer '+token
 r=urllib.request.Request(base+'/api/v1'+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
 with opener.open(r,timeout=30) as res:return json.load(res)
csrf=req('/auth/login',{'email':values['ADMIN_EMAIL'],'password':values['ADMIN_PASSWORD']})['csrf_token']
org=req('/organizations')['items'][0]['id'];project=req('/organizations/'+org+'/projects')['items'][0]['id'];env=req('/projects/'+project+'/environments')['items'][0]['id']
server=req('/environments/'+env+'/servers',{'display_name':'ci-synthetic-lab'})['id'];creds=req('/servers/'+server+'/agents',{})
now=datetime.datetime.now(datetime.timezone.utc).isoformat();a=hashlib.sha256(b'synthetic=1').hexdigest();b=hashlib.sha256(b'synthetic=2').hexdigest()
events=[{'event_uuid':str(uuid.uuid4()),'sequence':1,'file_alias':'ci-demo','kind':'baseline','old_sha256':'','new_sha256':a,'file_size':11,'observed_at':now},{'event_uuid':str(uuid.uuid4()),'sequence':2,'file_alias':'ci-demo','kind':'modified','old_sha256':a,'new_sha256':b,'file_size':11,'observed_at':now}]
req('/agent/events:batch',{'batch_id':str(uuid.uuid4()),'schema_version':1,'events':events},creds['token']);req('/agent/heartbeat',{'agent_version':'0.1.0','queue_depth':0,'observed_at':now},creds['token'])
print('Synthetic browser fixtures ready')
