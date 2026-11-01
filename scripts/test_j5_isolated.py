#!/usr/bin/env python3
"""Synthetic J5 integration against installed Coolify and an isolated local container."""
import json
import pathlib
import subprocess
import tempfile
import uuid
import j5_client
import j5_protocol

ROOT=pathlib.Path(__file__).resolve().parent.parent
source=(ROOT/'scripts/j5_coolify_transaction.php').read_text()+'\n?>\n'+(ROOT/'scripts/probe_j5_isolated.php').read_text()
r=subprocess.run(['ssh','-o','BatchMode=yes','contabo','docker exec -i coolify php'],input=source.encode(),capture_output=True,timeout=45)
if r.returncode or r.stderr:raise RuntimeError('Isolated Laravel probe failed; raw output withheld')
envelope=json.loads(r.stdout);assert envelope['status']=='ok'
d=envelope['data'];assert all(d[k] for k in ['sqlite_in_memory','fake_values_only','fault_rolled_back_all_writes','idempotent','invalid_digest_rejected','eloquent_encryption_roundtrip','installed_serializer_ran'])
variables=d.pop('serialized_synthetic_values')
try:j5_client.configure({})
except j5_protocol.J5Failure as e:
 assert e.diagnostic.category=='helper' and e.diagnostic.reason=='invalid_input' and e.diagnostic.exit_code==2 and e.diagnostic.phase=='apply' and e.diagnostic.kind=='runtime'
else:raise RuntimeError('Invalid input accepted')
with tempfile.TemporaryDirectory(prefix='configsentinel-j5-') as temp:
 path=pathlib.Path(temp);env=path/'synthetic.env';env.write_text(''.join(k+'='+v+'\n' for k,v in variables.items()));env.chmod(0o600)
 rendered=subprocess.run(['docker','compose','--env-file',str(env),'-p','oi6lvzwzomwtbbgzf5uzofuh','-f',str(ROOT/'deploy/compose.active-homologation.yml'),'config','--format','json'],capture_output=True,text=True,check=True,timeout=30)
 x=json.loads(rendered.stdout);assert x['volumes']['postgres_data']['external'] and x['volumes']['postgres_data']['name']=='oi6lvzwzomwtbbgzf5uzofuh_postgres_data';assert all(n['external'] for n in x['networks'].values());assert all(not v.get('ports') and not v.get('build') for v in x['services'].values());assert x['services']['api']['depends_on']['migrate']['condition']=='service_completed_successfully'
 manifest=json.loads((ROOT/'deploy/release-manifest.candidate.json').read_text())
 assert x['services']['api']['image']==manifest['api']['image'] and x['services']['migrate']['image']==manifest['api']['image']
 assert x['services']['web']['image']==manifest['web']['image'] and x['services']['db']['image']==manifest['db']['image']
 compose=path/'runtime.yml';compose.write_text('services:\n  test:\n    image: configsentinel-candidate-db:local\n    network_mode: none\n    entrypoint: ["sh", "-c", "printf %s \\\"$$VALUE\\\""]\n    environment:\n      VALUE: ${POSTGRES_PASSWORD}\n')
 r=subprocess.run(['docker','compose','--env-file',str(env),'-p','configsentinel-j5-serializer-'+uuid.uuid4().hex[:10],'-f',str(compose),'run','--rm','--no-deps','--pull','never','test'],capture_output=True,text=True,timeout=60)
 assert r.returncode==0 and r.stdout=="synthetic-$-hash#-quote'"
result={'probe':d,'invalid_input_envelope':'helper invalid_input phase apply kind runtime exit 2','synthetic_dollar_runtime_roundtrip':True,'compose_config_dollar_render_escapes_as_double':True,'volume_name':x['volumes']['postgres_data']['name'],'network_names':{k:v['name'] for k,v in x['networks'].items()},'no_ports_or_build':True,'active_configuration_writes':False,'full_active_deploy_exercised':False}
print(json.dumps(result,indent=2))
