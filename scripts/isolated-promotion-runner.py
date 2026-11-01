#!/usr/bin/env python3
"""Internal runner: unique isolated Compose only. No active volume/network permitted."""
import datetime as dt
import hashlib
import http.cookies
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid


def run(command, **kwargs):
    result = subprocess.run(command, capture_output=True, timeout=180, **kwargs)
    if result.returncode:
        raise RuntimeError('Isolated command failed: '+command[0]+' '+str(result.returncode))
    return result.stdout.decode()


def main():
    config = json.load(sys.stdin)
    project = config['project']
    if not re.fullmatch(r'configsentinel-prechecks-[a-f0-9]{10}', project):
        raise ValueError('Isolated project required')
    root = Path.home()/'.config'/project
    root.mkdir(mode=0o700, exist_ok=True)
    mode = config['mode']
    def private(name, value):
        path = root/name
        fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
    def compose(*args):
        return run(['docker', 'compose', '--project-name', project, '--project-directory', str(root), '--env-file', str(root/'.env'), '-f', str(root/'compose.yaml'), *args])
    def sql(query, role='configsentinel', auth=False):
        command = ['docker', 'exec', '-i']
        if auth:
            command += ['--env-file', str(root/'runtime-psql.env')]
        command += [project+'-db-1', 'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-v', 'VERBOSITY=sqlstate', '-U', role, '-d', 'configsentinel', '-At']
        if auth:
            command += ['-h', '127.0.0.1']
        return run(command, input=query.encode())
    def validate_scope():
        rendered = json.loads(compose('config', '--format', 'json'))
        assert set(rendered['services']) == {'api', 'web', 'db', 'migrate'}
        assert set(rendered['volumes']) == {'postgres_data'}
        assert rendered['volumes']['postgres_data']['name'] == project+'_postgres_data'
        assert not rendered['volumes']['postgres_data'].get('external')
        assert all(n.get('internal') and n['name'].startswith(project+'_') and not n.get('external') for n in rendered['networks'].values())
        for service in rendered['services'].values():
            assert not service.get('ports') and not service.get('build') and not service.get('network_mode')
            assert re.fullmatch(r'ghcr\.io/franklinlem/configsentinel-(api|web|db)@sha256:[a-f0-9]{64}', service['image'])
            assert service.get('pull_policy') == 'never'
            assert all(v['type'] == 'volume' and v['source'] == 'postgres_data' for v in service.get('volumes', []))
            assert service['labels'].get('traefik.enable') == 'false'
    def wait_db():
        for _ in range(60):
            r = subprocess.run(['docker', 'exec', project+'-db-1', 'pg_isready', '-h', '127.0.0.1', '-U', 'configsentinel'], capture_output=True)
            if r.returncode == 0:
                return
            time.sleep(1)
        raise RuntimeError('Isolated database timeout')
    if mode == 'validate-only':
        validate_scope()
        print(json.dumps({'isolated_scope_validated': True, 'services_started': False}))
        return
    if mode == 'setup':
        private('compose.yaml', config['compose'])
        private('.env', config['env'])
        private('roles.env', config['roles_env'])
        private('runtime-psql.env', config['runtime_psql_env'])
        private('adopt.sql', config['adopt_sql'])
        validate_scope()
        (root/'empty-init').mkdir(exist_ok=True)
        # Mimic the already-initialized RC1 database: no new-image init roles.
        private('init.override.yaml', 'services:\n  db:\n    volumes:\n      - '+str(root/'empty-init')+':/docker-entrypoint-initdb.d:ro\n')
        compose('-f', str(root/'init.override.yaml'), 'up', '-d', '--pull', 'never', '--no-build', 'db')
        wait_db()
        assert sql("SELECT count(*) FROM pg_roles WHERE rolname IN ('configsentinel_owner','configsentinel_runtime','configsentinel_migrator');").strip() == '0'
        print(json.dumps({'project': project, 'initial_application_roles': 0, 'public_ports': False, 'live_volume_attached': False}))
        return
    if mode != 'exercise':
        raise ValueError('Unknown isolated operation')
    validate_scope()
    wait_db()
    tables = ['schema_migrations','organizations','users','projects','memberships','environments','servers','agents','agent_tokens','user_sessions','change_events','file_observations','acknowledgements','audit_logs']
    def counts():
        return {t: int(sql('SELECT count(*) FROM '+t+';').strip()) for t in tables}
    baseline = counts()
    before = sql('SELECT max(version) FROM schema_migrations;').strip()
    assert before == '1' and baseline['users'] > 0
    run(['docker', 'exec', '-i', '--env-file', str(root/'roles.env'), '-e', 'PGOPTIONS=-c lock_timeout=5s -c statement_timeout=60s -c log_statement=none -c log_min_error_statement=panic', project+'-db-1', 'psql', '-X', '--single-transaction', '-v', 'ON_ERROR_STOP=1', '-U', 'configsentinel', '-d', 'configsentinel', '-f', '-'], input=(root/'adopt.sql').read_bytes())
    assert counts() == baseline
    allowed = sql("SELECT current_user,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user;", 'configsentinel_runtime', True).strip()
    assert allowed == 'configsentinel_runtime|f|f|f|f'
    sql("BEGIN; INSERT INTO audit_logs(id,organization_id,operation,target_type,target_id) SELECT gen_random_uuid(),id,'synthetic.precheck','organization',id FROM organizations LIMIT 1; ROLLBACK;", 'configsentinel_runtime', True)
    denied = []
    for query in ['CREATE TABLE public.forbidden(id integer)', 'CREATE SCHEMA forbidden', 'ALTER TABLE users ADD COLUMN forbidden text', 'TRUNCATE audit_logs', 'UPDATE audit_logs SET operation=operation WHERE false', 'DELETE FROM audit_logs WHERE false', 'UPDATE schema_migrations SET version=version', 'SET ROLE configsentinel_owner', 'SET ROLE configsentinel_migrator', 'ALTER ROLE configsentinel_runtime SUPERUSER']:
        command = ['docker','exec','-i','--env-file',str(root/'runtime-psql.env'),project+'-db-1','psql','-X','-h','127.0.0.1','-U','configsentinel_runtime','-d','configsentinel','-v','ON_ERROR_STOP=1','-v','VERBOSITY=sqlstate']
        r = subprocess.run(command,input=('BEGIN; '+query+'; ROLLBACK;').encode(),capture_output=True,timeout=20)
        assert r.returncode != 0 and b'42501' in r.stderr
        denied.append(query.split()[0])
    stages = []
    sessions = {}
    viewer_password = secrets.token_hex(24)
    viewer_email = project+'@example.invalid'
    origin = 'https://configsentinel-dev.franklem.uk'
    for index, (stage, image) in enumerate([('candidate', config['candidate_api']), ('fallback', config['fallback_api']), ('return-candidate', config['candidate_api'])]):
        env = (root/'.env').read_text()
        env = re.sub(r'^CONFIGSENTINEL_API_IMAGE=.*$', 'CONFIGSENTINEL_API_IMAGE='+image, env, flags=re.M)
        private('.env', env)
        # This is the exact command generated by installed Coolify's injection helper.
        import shlex
        run(shlex.split(config['injected_start_command']))
        web = json.loads(run(['docker','inspect',project+'-web-1']))[0]
        assert not web['HostConfig']['PortBindings']
        address = next(iter(web['NetworkSettings']['Networks'].values()))['IPAddress']
        base = 'http://'+address+':8080'
        def request(path, body=None, session=None, token=None, csrf=True):
            headers = {'Content-Type':'application/json', 'Origin':origin}
            if session:
                headers['Cookie'] = session['cookie']
                if csrf:
                    headers['X-CSRF-Token'] = session['csrf']
            if token:
                headers['Authorization'] = 'Bearer '+token
            req = urllib.request.Request(base+path, headers=headers, data=None if body is None else json.dumps(body).encode())
            try:
                with urllib.request.urlopen(req, timeout=15) as response:
                    payload = response.read()
                    return response.status, json.loads(payload) if payload else {}, response.headers
            except urllib.error.HTTPError as error:
                return error.code, {}, error.headers
        for _ in range(90):
            try:
                if request('/api/health/ready')[0] == 200:
                    break
            except (OSError,ValueError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError('Isolated readiness failed')
        assert request('/api/v1/events')[0] == 401
        def login(email, password):
            code, body, headers = request('/api/v1/auth/login', {'email':email,'password':password})
            assert code == 200
            cookie = http.cookies.SimpleCookie();cookie.load(headers.get('Set-Cookie'))
            assert all(v['secure'] and v['httponly'] for v in cookie.values())
            return {'csrf':body['csrf_token'], 'cookie':'; '.join(k+'='+v.value for k,v in cookie.items())}
        owner = login(config['login']['email'], config['login']['password'])
        if index == 0:
            org = request('/api/v1/organizations',session=owner)[1]['items'][0]['id']
        if index == 0:
            assert request('/api/v1/organizations/'+org+'/members',{'email':viewer_email,'password':viewer_password,'role':'viewer'},owner)[0] == 201
            foreign = request('/api/v1/organizations',{'name':'Isolated boundary','slug':project},owner)
            assert foreign[0] == 201
            foreign_org = foreign[1]['id']
            project_id = request('/api/v1/organizations/'+org+'/projects',session=owner)[1]['items'][0]['id']
            environment = request('/api/v1/projects/'+project_id+'/environments',session=owner)[1]['items'][0]['id']
            server = request('/api/v1/environments/'+environment+'/servers',{'display_name':'isolated-synthetic-only'},owner)
            assert server[0] == 201
            credentials = request('/api/v1/servers/'+server[1]['id']+'/agents',{},owner)
            assert credentials[0] == 201
            agent_token = credentials[1]['token']
        viewer = login(viewer_email, viewer_password)
        assert request('/api/v1/organizations/'+org+'/projects',session=viewer)[0] == 200
        assert request('/api/v1/organizations/'+org+'/projects',{'name':'denied','slug':'denied'},viewer)[0] == 403
        assert request('/api/v1/organizations/'+foreign_org+'/projects',session=viewer)[0] in (403,404)
        assert request('/api/v1/organizations/'+org+'/projects',{'name':'denied','slug':'denied'},owner,csrf=False)[0] == 403
        event = {'event_uuid':str(uuid.uuid4()),'sequence':index+1,'file_alias':'isolated-fixture','kind':'baseline','old_sha256':'','new_sha256':hashlib.sha256(('synthetic'+str(index)).encode()).hexdigest(),'file_size':10,'observed_at':dt.datetime.now(dt.timezone.utc).isoformat()}
        before_events = int(sql('SELECT count(*) FROM change_events;').strip())
        for _ in range(2):
            code = request('/api/v1/agent/events:batch',{'batch_id':str(uuid.uuid4()),'schema_version':1,'events':[event]},token=agent_token)[0]
            assert code in (200,201,202)
        assert int(sql('SELECT count(*) FROM change_events;').strip()) == before_events+1
        assert request('/api/v1/agent/heartbeat',{'agent_version':'0.1.0','queue_depth':0,'observed_at':dt.datetime.now(dt.timezone.utc).isoformat()},token=agent_token)[0] == 202
        assert request('/api/v1/events',session=owner)[0] == 200
        assert request('/api/v1/organizations/'+org+'/audit-logs',session=owner)[0] == 200
        assert request('/api/v1/auth/logout',{},owner)[0] in (200,204)
        assert request('/api/v1/me',session=owner)[0] == 401
        assert sql('SELECT max(version) FROM schema_migrations;').strip() == '1'
        assert int(sql('SELECT count(*) FROM acknowledgements;').strip()) == baseline['acknowledgements']
        stages.append({'stage':stage,'api_image':image,'migration_image':config['candidate_api'],'readiness':200,'login':True,'rbac_denied':403,'tenant_boundary_denied':True,'csrf_denied':403,'events_and_replay_passed':True,'heartbeat':202,'audit_readable':True,'logout_invalidates_session':True,'schema':1,'events':before_events+1,'acknowledgements':baseline['acknowledgements']})
    compose('stop','--timeout','30')
    print(json.dumps({'project':project,'live_volumes_attached':False,'public_ports':False,'initial_restored_counts':baseline,'adoption_preserved_all_table_counts':True,'runtime_authenticated_over_tcp':True,'denied_operations':len(denied),'stages':stages,'all_isolated_services_stopped':True,'isolated_volume_preserved':True,'full_coolify_job_executed':False},indent=2))


if __name__ == '__main__':
    main()
