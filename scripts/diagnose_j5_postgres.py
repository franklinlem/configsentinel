#!/usr/bin/env python3
"""Run J5 diagnostics ONLY against an existing dedicated synthetic PostgreSQL container."""
import dataclasses
import json
import pathlib
import re
import shlex
import subprocess
import sys
import uuid

from j5_protocol import J5Failure, decode_response

ROOT=pathlib.Path(__file__).resolve().parent.parent
context=json.loads(pathlib.Path(sys.argv[1]).read_text())
name=context['name'];assert re.fullmatch(r'configsentinel-j5-diagnostic-[a-f0-9]{10}',name)
assert context['environment_file']=='/home/franklin/.config/'+name+'/synthetic.env'

def ssh(args, *, data=None, phase, allow_failure=False):
    command=' '.join(shlex.quote(x) for x in args)
    r=subprocess.run(['ssh','-o','BatchMode=yes','contabo',command],input=data,capture_output=True,timeout=90)
    log={'phase':phase,'category':'success','exit_code':r.returncode,'stdout_bytes':len(r.stdout),'stderr_bytes':len(r.stderr)}
    if (r.returncode and not allow_failure) or r.stderr:
        log['category']='transport_or_helper'
        raise RuntimeError(json.dumps({'reason':'nonzero_exit_or_unexpected_stderr',**log}))
    return r,log

network, _ = ssh(['docker','network','inspect',name+'-net'],phase='scope_network')
net=json.loads(network.stdout)[0];assert net['Internal'] and net['Id']==context['network_id']
assert {v['Name'] for v in net['Containers'].values()} == {name+'-db'}
db,_=ssh(['docker','inspect',name+'-db'],phase='scope_database');db=json.loads(db.stdout)[0]
assert db['Id']==context['db_container_id'] and db['Image']==context['db_image_id'] and not db['HostConfig']['PortBindings'] and all(x['Type']!='volume' for x in db['Mounts'])
assert set(db['NetworkSettings']['Networks'])=={name+'-net'}
db_image,_=ssh(['docker','inspect','--format','{{.Image}}','coolify-db'],phase='scope_db_image_installed')
assert db_image.stdout.decode().strip()==context['db_image_id']
permissions,_=ssh(['stat','-c','%a',context['environment_file']],phase='scope_credential_mode')
assert permissions.stdout.strip()==b'600'
current,_=ssh(['docker','inspect','--format','{{.Image}}','coolify'],phase='scope_image_installed')
image,_=ssh(['docker','image','inspect','--format','{{.Id}}','coollabsio/coolify:4.5.3'],phase='scope_image_clone')
assert current.stdout.strip()==image.stdout.strip()
logs=[];tag=uuid.uuid4().hex[:12]
common=['docker','run','--rm','-i','--network',name+'-net','--env-file',context['environment_file']]
def php_run(database,source,*,payload=None,phase,allow_failure=False):
    args=common+['-e','DB_DATABASE='+database,'--entrypoint','php','coollabsio/coolify:4.5.3']
    if payload is None:return ssh(args,data=source.encode(),phase=phase)
    return ssh(args+['-r',source],data=json.dumps(payload).encode(),phase=phase,allow_failure=allow_failure)

for kind in ('entry','buffer'):
    database='j5_'+kind+'_'+tag
    _,log=ssh(['docker','exec',name+'-db','createdb','-U','j5_synthetic',database],phase='create_'+kind+'_database');logs.append(log)
    fixture=(ROOT/'scripts/diagnose_j5_pg_fixture.php').read_text();r,log=php_run(database,fixture,phase='fixture_'+kind);logs.append(log)
    fixture_result=json.loads(r.stdout);assert fixture_result['scope_verified'] and fixture_result['synthetic_key_only']
manifest=json.loads((ROOT/'deploy/release-manifest.candidate.json').read_text());api=manifest['api']['image'];web=manifest['web']['image'];pg=manifest['db']['image'];fallback=json.loads((ROOT/'deploy/release-manifest.fallback.json').read_text())['api']['image']
payload={'mode':'active','uuid':'oi6lvzwzomwtbbgzf5uzofuh','commit':'36baf66f4656f86d157cd070202323db9465c5f4','branch':'plan/active-homologation-rc2','compose':'/deploy/compose.active-homologation.yml','custom_build':"docker image inspect --format '{{.Id}}' "+' '.join(image.rsplit('@',1)[1] for image in [api,web,pg]),'custom_start':'docker compose --env-file .env -f ./deploy/compose.active-homologation.yml --project-name oi6lvzwzomwtbbgzf5uzofuh up -d --pull never --no-build','env':{'POSTGRES_PASSWORD':'synthetic-password-only','RUNTIME_DB_PASSWORD':'1'*64,'MIGRATOR_DB_PASSWORD':'2'*64,'CONFIGSENTINEL_API_IMAGE':api,'CONFIGSENTINEL_MIGRATION_IMAGE':api,'CONFIGSENTINEL_WEB_IMAGE':web,'CONFIGSENTINEL_DB_IMAGE':pg}}
source='?>\n'+(ROOT/'scripts/j5_coolify_transaction.php').read_text()+'\n?>\n'+(ROOT/'scripts/j5_coolify_entry.php').read_text()
for iteration in (1,2):
    r,log=php_run('j5_entry_'+tag,source,payload=payload,phase='entry_'+str(iteration));logs.append(log)
    result=decode_response(r.returncode,r.stdout,r.stderr);assert result['changed']==(iteration==1)
    log.update({'category':'success','changed':result['changed']})
r,log=php_run('j5_missing_'+tag,source,payload=payload,phase='synthetic_missing_database',allow_failure=True)
try:
    decode_response(r.returncode,r.stdout,r.stderr)
    raise AssertionError('synthetic missing database unexpectedly accepted')
except J5Failure as error:
    assert error.diagnostic.category=='helper' and error.diagnostic.reason=='internal_error' and error.diagnostic.phase=='apply' and error.diagnostic.kind=='database'
    log.update({'category':error.diagnostic.category,'helper_phase':error.diagnostic.phase,'kind':error.diagnostic.kind})
logs.append(log)
source=(ROOT/'scripts/j5_coolify_transaction.php').read_text()+'\n?>\n'+(ROOT/'scripts/diagnose_j5_buffer.php').read_text();r,log=php_run('j5_buffer_'+tag,source,phase='injected_buffer');logs.append(log);buffer=json.loads(r.stdout);assert buffer['rollback_identical'] and buffer['clean_first_change'] and buffer['clean_second_idempotent'] and buffer['noisy_attempt_result']=='internal_error' and buffer['warning_maps_to_internal_error'] and buffer['database_exception_maps_to_internal_error'];log['category']='success'
print(json.dumps({'scope':'dedicated internal network and synthetic PostgreSQL 15 with Coolify image identical to installed','helper_entry_first_success':True,'helper_entry_idempotent':True,'missing_database_sanitized_kind_verified':True,'buffer_probe':buffer,'logs':logs,'raw_output_or_live_secrets_persisted':False,'synthetic_fixtures_preserved':True},indent=2))
