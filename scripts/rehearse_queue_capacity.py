#!/usr/bin/env python3
"""Migrate and roll back only a newly restored, isolated homologation copy."""
import argparse,json,re,secrets,shlex,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--restore-target',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True);p.add_argument('--fallback',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 target=json.loads(args.restore_target.read_text()); candidate=json.loads(args.candidate.read_text());fallback=json.loads(args.fallback.read_text())
 for record in (candidate,fallback):
  if not record.get('signature_verified') or not record.get('provenance_verified') or record.get('scan_high')!=0 or record.get('scan_critical')!=0 or not re.fullmatch(r'ghcr\.io/franklinlem/configsentinel-api@sha256:[0-9a-f]{64}',record.get('image','')):raise SystemExit('unverified API image')
 if not re.fullmatch(r'configsentinel-j3-only-[a-f0-9]{12}-db',target.get('container_name','')) or not target.get('network_internal') or target.get('public_ports') or target.get('active_volume_mounted'):raise SystemExit('invalid isolated target')
 payload={'target':target,'candidate':candidate['image'],'fallback':fallback['image'],'provision':Path('db/roles/provision.sql').read_text(),'grants':Path('db/roles/runtime-grants.sql').read_text(),'runtime':secrets.token_hex(32),'migrator':secrets.token_hex(32)}
 code=r'''import sys,json,subprocess,time,uuid
p=json.load(sys.stdin);t=p['target'];db=t['container_name'];prefix='configsentinel-capacity-rehearsal-'+uuid.uuid4().hex[:10]
def run(args,data=None,check=True):
 r=subprocess.run(args,input=data,text=True,capture_output=True,timeout=100)
 if check and r.returncode:raise RuntimeError('failed '+args[1]+' status '+str(r.returncode))
 return r.stdout.strip()
x=json.loads(run(['docker','inspect',db]))[0];n=json.loads(run(['docker','network','inspect',t['network_id']]))[0]
assert x['Id']==t['container_id'] and x['State']['Running'] and not x['HostConfig']['PortBindings'] and n['Internal'] and set(n['Containers'])=={t['container_id']}
assert all(m.get('Name')!='oi6lvzwzomwtbbgzf5uzofuh_postgres_data' for m in x['Mounts'])
net=n['Name']
for im in (p['candidate'],p['fallback']):run(['docker','image','inspect',im])
def sql(s):return run(['docker','exec','-i',db,'psql','-X','-U','configsentinel','-d','configsentinel','-At','-v','ON_ERROR_STOP=1'],s)
q="SELECT json_build_object('events',(SELECT md5(coalesce(string_agg(to_jsonb(e)::text,'' ORDER BY e.id),'')) FROM change_events e),'acknowledgements',(SELECT md5(coalesce(string_agg(to_jsonb(a)::text,'' ORDER BY a.id),'')) FROM acknowledgements a),'event_count',(SELECT count(*) FROM change_events),'ack_count',(SELECT count(*) FROM acknowledgements));"
before=json.loads(sql(q));assert before['event_count']==4 and before['ack_count']==2 and sql('SELECT max(version) FROM schema_migrations')=='1'
run(['docker','exec','-i','-e','CONFIGSENTINEL_RUNTIME_PASSWORD='+p['runtime'],'-e','CONFIGSENTINEL_MIGRATOR_PASSWORD='+p['migrator'],db,'psql','-X','-U','configsentinel','-d','configsentinel','-v','ON_ERROR_STOP=1'],p['provision'])
sql('SET ROLE configsentinel_owner;\n'+p['grants'])
assert json.loads(sql(q))==before
common=['--network',net,'--read-only','--cap-drop=ALL','--security-opt=no-new-privileges:true','-e','PUBLIC_URL=https://example.invalid','-e','COOKIE_SECURE=true']
def launch(name,image,role,password,command=None):
 args=['docker','run','-d','--name',prefix+'-'+name]+common+['-e','DATABASE_URL=postgresql://'+role+':'+password+'@'+db+':5432/configsentinel?sslmode=disable',image]
 if command:args+=command
 return run(args)
def ready(name):
 for _ in range(45):
  r=subprocess.run(['docker','exec',prefix+'-'+name,'wget','-qO-','http://127.0.0.1:8081/api/health/ready'],capture_output=True)
  if r.returncode==0:return
  time.sleep(1)
 raise RuntimeError('readiness failed '+name)
ids={};ids['fallback_v1']=launch('fallback-v1',p['fallback'],'configsentinel_runtime',p['runtime']);ready('fallback-v1');run(['docker','stop',prefix+'-fallback-v1'])
ids['migrate']=launch('migrate',p['candidate'],'configsentinel_migrator',p['migrator'],['/app/server','--migrate'])
exitcode=run(['docker','wait',prefix+'-migrate']);assert exitcode=='0' and sql('SELECT max(version) FROM schema_migrations')=='2' and json.loads(sql(q))==before
ids['candidate']=launch('candidate',p['candidate'],'configsentinel_runtime',p['runtime']);ready('candidate');run(['docker','stop',prefix+'-candidate'])
ids['fallback_v2']=launch('fallback-v2',p['fallback'],'configsentinel_runtime',p['runtime']);ready('fallback-v2');run(['docker','stop',prefix+'-fallback-v2'])
assert json.loads(sql(q))==before
print(json.dumps({'status':'PASS','schema_before':1,'schema_after':2,'fallback_v1':'PASS','candidate_v2':'PASS','fallback_v2':'PASS','event_and_ack_identity_preserved':True,'event_count':before['event_count'],'acknowledgements_count':before['ack_count'],'network_id':t['network_id'],'test_db':db,'containers':ids,'public_ports':False,'active_database_modified':False,'resources_preserved':True}))'''
 r=subprocess.run(['ssh','-o','BatchMode=yes','contabo','python3 -c '+shlex.quote(code)],input=json.dumps(payload),text=True,capture_output=True,timeout=300)
 if r.returncode:raise SystemExit('rehearsal failed; exit='+str(r.returncode)+' stdout_bytes='+str(len(r.stdout))+' stderr_bytes='+str(len(r.stderr)))
 result=json.loads(r.stdout);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
