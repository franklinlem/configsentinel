#!/usr/bin/env python3
"""Rehearse digest upgrade/rollback on an isolated copy on the homologation host.

Never attaches a live volume, exposes a port or changes a Coolify resource.
Only starts/stops its uniquely named containers; keeps the test volume intact.
"""
import argparse
import json
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import time

PREFIX='configsentinel-rehearsal-'


def remote(code, payload=None):
    result=subprocess.run(['ssh','contabo','python3 -c '+shlex.quote(code)],input=None if payload is None else json.dumps(payload),capture_output=True,text=True,check=True,timeout=240)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('artifacts',type=Path);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    records={v['component']:v for p in args.artifacts.glob('**/image.json') for v in [json.loads(p.read_text())]}
    assert all(records[n]['scan_high']==0 and records[n]['scan_critical']==0 and records[n]['provenance_verified'] is True for n in ['api','web','db'])
    for name,value in records.items():
        assert re.fullmatch(r'ghcr\.io/franklinlem/configsentinel-'+name+r'@sha256:[0-9a-f]{64}',value['image'])
    recovery=json.loads(Path('docs/evidence/remediation/recovery-point.json').read_text())
    run=secrets.token_hex(5)
    settings={'prefix':PREFIX+run,'images':{n:v['image'] for n,v in records.items()},'previous':{n:v['image_id'] for n,v in recovery['images'].items()},'passwords':{n:secrets.token_hex(24) for n in ['admin','runtime','migrator']}}
    setup=r'''
import json,sys,subprocess,pathlib,os
c=json.load(sys.stdin);prefix=c['prefix'];root=pathlib.Path.home()/'.config'/prefix;root.mkdir(mode=0o700)
def env(name,items):
 p=root/(name+'.env');p.write_text(''.join(k+'='+v+'\n' for k,v in items.items()));p.chmod(0o600)
p=c['passwords'];common={'PUBLIC_URL':'https://configsentinel-dev.franklem.uk','COOKIE_SECURE':'true'}
env('db',{'POSTGRES_USER':'configsentinel','POSTGRES_DB':'configsentinel','POSTGRES_PASSWORD':p['admin'],'CONFIGSENTINEL_RUNTIME_PASSWORD':p['runtime'],'CONFIGSENTINEL_MIGRATOR_PASSWORD':p['migrator']})
for name in ['runtime','migrator']:env(name,dict(common,DATABASE_URL='postgresql://configsentinel_'+name+':'+p[name]+'@db:5432/configsentinel?sslmode=disable'))
for cmd in [['docker','network','create','--internal',prefix],['docker','volume','create',prefix+'-data'],['docker','run','-d','--name',prefix+'-db-candidate','--label','io.configsentinel.scope=rehearsal','--network',prefix,'--network-alias','db','--env-file',str(root/'db.env'),'--mount','type=volume,source='+prefix+'-data,target=/var/lib/postgresql/data',c['images']['db']]]:subprocess.run(cmd,check=True,capture_output=True)
print(json.dumps({'prefix':prefix}))
'''
    remote(setup,settings)
    prefix=settings['prefix']
    def db_ready(suffix):
        for _ in range(60):
            r=subprocess.run(['ssh','contabo','docker exec '+prefix+'-db-'+suffix+' pg_isready -h 127.0.0.1 -U configsentinel -d configsentinel'],capture_output=True)
            if r.returncode==0:return
            time.sleep(1)
        raise RuntimeError('Isolated database did not become ready')
    db_ready('candidate')
    decrypt=r"""import os,pathlib,re; p=pathlib.Path.home()/'.local/share/configsentinel-backups'; name=(p/'last-success.txt').read_text().split()[1]; assert re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T\d{12}Z)?\.dump\.gpg',name); os.execvp('gpg',['gpg','--batch','--pinentry-mode','loopback','--passphrase-file',str(pathlib.Path.home()/'.config/configsentinel-backup/encryption.key'),'--decrypt',str(p/'daily'/name)])"""
    # Credentials and plaintext dump are streamed only; no plaintext dump file.
    source=subprocess.Popen(['ssh','frank-note2','python3 -c '+shlex.quote(decrypt)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    restored=subprocess.run(['ssh','contabo','docker exec -i '+prefix+'-db-candidate pg_restore -U configsentinel -d configsentinel --no-owner --no-acl --exit-on-error'],stdin=source.stdout,capture_output=True,timeout=120)
    source.stdout.close();source.communicate(timeout=120)
    if source.returncode or restored.returncode:raise RuntimeError('Isolated encrypted restore failed')
    remote(r'''
import json,sys,subprocess,pathlib
c=json.load(sys.stdin);p=c['prefix'];root=pathlib.Path.home()/'.config'/p
subprocess.run(['docker','exec',p+'-db-candidate','psql','-U','configsentinel','-d','configsentinel','-v','ON_ERROR_STOP=1','-f','/opt/configsentinel/provision.sql'],capture_output=True,check=True)
subprocess.run(['docker','run','--rm','--name',p+'-migrate','--network',p,'--env-file',str(root/'migrator.env'),c['images']['api'],'/app/server','--migrate'],capture_output=True,check=True)
''',settings)
    exercise=r'''
import json,sys,subprocess,pathlib,time
c=json.load(sys.stdin);p=c['prefix'];root=pathlib.Path.home()/'.config'/p;stage=c['stage'];role=c['role'];db=c['database']
def command(args):return subprocess.run(['docker']+args,capture_output=True,text=True,check=True).stdout.strip()
for n in ['api','web']:
 args=['run','-d','--name',p+'-'+n+'-'+stage,'--label','io.configsentinel.scope=rehearsal','--network',p,'--cap-drop=ALL','--security-opt=no-new-privileges:true']
 if n=='api':args+=['--network-alias','api','--read-only','--env-file',str(root/'runtime.env')]
 args+=[c['images'][n] if role=='candidate' else c['previous'][n]]
 command(args)
for _ in range(60):
 check=subprocess.run(['docker','exec',p+'-web-'+stage,'wget','-q','-O','-','http://127.0.0.1:8080/api/health/ready'],capture_output=True,text=True)
 if check.returncode==0:break
 time.sleep(1)
else:raise RuntimeError('Isolated readiness failed')
auth=subprocess.run(['docker','exec',p+'-web-'+stage,'wget','-S','-O','/dev/null','http://127.0.0.1:8080/api/v1/events'],capture_output=True,text=True)
assert '401' in auth.stderr
counts=command(['exec',p+'-db-'+db,'psql','-U','configsentinel','-d','configsentinel','-Atc',"SELECT json_build_object('schema',(SELECT max(version) FROM schema_migrations),'events',(SELECT count(*) FROM change_events),'acknowledgements',(SELECT count(*) FROM acknowledgements),'version',current_setting('server_version'))"])
for n in ['web','api']:command(['stop',p+'-'+n+'-'+stage])
print(json.dumps({'stage':stage,'ready':True,'unauthenticated_status':401,'counts':json.loads(counts)}))
'''
    evidence=[]
    evidence.append(remote(exercise,{**settings,'stage':'candidate','role':'candidate','database':'candidate'}))
    evidence.append(remote(exercise,{**settings,'stage':'rollback-app','role':'previous','database':'candidate'}))
    remote(r'''
import json,sys,subprocess,pathlib
c=json.load(sys.stdin);p=c['prefix'];root=pathlib.Path.home()/'.config'/p
subprocess.run(['docker','stop',p+'-db-candidate'],capture_output=True,check=True)
subprocess.run(['docker','run','-d','--name',p+'-db-rollback','--label','io.configsentinel.scope=rehearsal','--network',p,'--network-alias','db','--env-file',str(root/'db.env'),'--mount','type=volume,source='+p+'-data,target=/var/lib/postgresql/data',c['previous']['db']],capture_output=True,check=True)
''',settings)
    db_ready('rollback')
    evidence.append(remote(exercise,{**settings,'stage':'rollback-db','role':'previous','database':'rollback'}))
    remote("import json,sys,subprocess; p=json.load(sys.stdin)['prefix']; subprocess.run(['docker','stop',p+'-db-rollback'],capture_output=True,check=True); subprocess.run(['docker','start',p+'-db-candidate'],capture_output=True,check=True)",settings)
    db_ready('candidate')
    evidence.append(remote(exercise,{**settings,'stage':'return-candidate','role':'candidate','database':'candidate'}))
    assert all(v['counts']==evidence[0]['counts'] for v in evidence)
    remote("import json,sys,subprocess; p=json.load(sys.stdin)['prefix']; subprocess.run(['docker','stop',p+'-db-candidate'],capture_output=True,check=True)",settings)
    args.output.write_text(json.dumps({'prefix':prefix,'isolated':True,'live_volumes_attached':False,'public_ports':False,'volume_preserved':True,'all_containers_stopped':True,'stages':evidence},indent=2)+'\n')
    print('Isolated homologation upgrade/rollback passed; original application untouched')


if __name__=='__main__':main()
