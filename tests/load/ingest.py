"""Bounded localhost benchmark: 25 synthetic agents, batches of 100 metadata events."""
import concurrent.futures,datetime,hashlib,http.cookiejar,json,statistics,time,urllib.request,uuid
from pathlib import Path
values=dict(l.split('=',1) for l in Path('.local/dev.env').read_text().splitlines());base='http://localhost:8080';csrf=''
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(path,body=None):
 r=urllib.request.Request(base+'/api/v1'+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':base,'X-CSRF-Token':csrf})
 with opener.open(r,timeout=30) as res:return json.load(res)
csrf=req('/auth/login',{'email':values['ADMIN_EMAIL'],'password':values['ADMIN_PASSWORD']})['csrf_token']
org=req('/organizations')['items'][0]['id'];project=req('/organizations/'+org+'/projects')['items'][0]['id'];env=req('/projects/'+project+'/environments')['items'][0]['id'];agents=[]
for i in range(25):
 server=req('/environments/'+env+'/servers',{'display_name':'load-'+str(i)})['id'];agents.append(req('/servers/'+server+'/agents',{}))
now=datetime.datetime.now(datetime.timezone.utc).isoformat();h=hashlib.sha256(b'synthetic benchmark fixture').hexdigest()
def batch(credential):
 events=[{'event_uuid':str(uuid.uuid4()),'sequence':i+1,'file_alias':'fixture-'+str(i),'kind':'baseline','new_sha256':h,'file_size':27,'observed_at':now} for i in range(100)]
 body=json.dumps({'batch_id':str(uuid.uuid4()),'schema_version':1,'events':events}).encode();r=urllib.request.Request(base+'/api/v1/agent/events:batch',data=body,headers={'Content-Type':'application/json','Authorization':'Bearer '+credential['token']});start=time.perf_counter()
 with urllib.request.urlopen(r,timeout=30) as res:out=json.load(res)
 assert len(out['accepted'])==100
 return (time.perf_counter()-start)*1000
started=time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:durations=list(pool.map(batch,agents))
result={'environment':'local Docker; five concurrent batches','agents':25,'events':2500,'batch_size':100,'duration_seconds':round(time.perf_counter()-started,3),'p50_batch_ms':round(statistics.median(durations),2),'p95_batch_ms':round(sorted(durations)[23],2),'max_batch_ms':round(max(durations),2),'errors':0}
Path('.local/load-evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
