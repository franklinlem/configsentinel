import base64,json,os,pathlib,secrets,stat,subprocess,time,uuid
os.umask(0o077)
name='configsentinel-j5-diagnostic-'+uuid.uuid4().hex[:10];root=pathlib.Path.home()/'.config'/name;root.mkdir(mode=0o700)
pw=secrets.token_hex(32);key='base64:'+base64.b64encode(secrets.token_bytes(32)).decode();env=root/'synthetic.env'
fd=os.open(env,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:f.write('\n'.join(['POSTGRES_USER=j5_synthetic','POSTGRES_DB=j5_synthetic','POSTGRES_PASSWORD='+pw,'DB_CONNECTION=pgsql','DB_HOST='+name+'-db','DB_PORT=5432','DB_DATABASE=j5_synthetic','DB_USERNAME=j5_synthetic','DB_PASSWORD='+pw,'APP_KEY='+key,'APP_ENV=testing'])+'\n')
def run(a):
 r=subprocess.run(a,capture_output=True,timeout=60)
 if r.returncode:raise RuntimeError('isolated_command_failed:'+a[1])
 return r.stdout.decode().strip()
image=json.loads(run(['docker','inspect','coolify-db']))[0]['Image'];run(['docker','image','inspect',image]);net=run(['docker','network','create','--internal',name+'-net']);db=run(['docker','run','-d','--name',name+'-db','--network',name+'-net','--memory','256m','--tmpfs','/var/lib/postgresql/data:rw,size=128m','--env-file',str(env),image]);
for _ in range(60):
 st=json.loads(run(['docker','inspect',db]))[0]
 if st['State']['Status']=='exited':raise RuntimeError('isolated_db_exited')
 if subprocess.run(['docker','exec',db,'pg_isready','-h','127.0.0.1','-U','j5_synthetic'],capture_output=True).returncode==0:break
 time.sleep(1)
else:raise RuntimeError('isolated_db_timeout')
n=json.loads(run(['docker','network','inspect',net]))[0];x=json.loads(run(['docker','inspect',db]))[0];assert n['Internal'] and not x['HostConfig']['PortBindings'] and all(m['Type']!='volume' for m in x['Mounts']);assert stat.S_IMODE(env.stat().st_mode)==0o600
print(json.dumps({'name':name,'network_id':net,'db_container_id':db,'db_image_id':image,'environment_file':str(env),'isolated_internal_network':True,'no_public_ports':True,'database_tmpfs_only':True,'credential_mode':'0600','pg_isready':True}))
