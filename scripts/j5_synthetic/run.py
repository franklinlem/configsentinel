#!/usr/bin/env python3
"""Execute ONLY a new synthetic J5 environment; never clean up or query active DBs.
Run this packaged directory on the Docker host. Stdout is a sanitized report.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import subprocess
import tarfile
import time
import uuid

COOLIFY = 'sha256:e4e662978b1ea86b9711149caa2e46497bf8f2c03f578c45324d33e42914ff61'
POSTGRES = 'sha256:54e0dd8e8cddcdbb9156c2486eed5a43eccb7214d7c6828097d41ce049fb3984'
DISABLED = 'exec,system,passthru,shell_exec,proc_open,popen,pcntl_exec'
ROOT = Path(__file__).resolve().parent
REPORT = {'result': 'FAIL', 'active_metadata_read': False, 'deploy_attempted': False,
          'resources_preserved': True, 'resources': {}, 'steps': []}


def run(args, *, phase, data=None, allowed=(0,), timeout=45):
    try:
        r = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('timeout:' + phase) from None
    REPORT['steps'].append({'phase': phase, 'exit_code': r.returncode,
                            'stdout_bytes': len(r.stdout), 'stderr_bytes': len(r.stderr)})
    if r.returncode not in allowed:
        raise RuntimeError('command_failed:' + phase)
    return r


def docker(*args, **kwargs):
    return run(['docker', *args], **kwargs)


def inspect_resource(kind, name):
    return json.loads(docker(kind, 'inspect', name, phase='inspect_' + kind).stdout)[0]


def exercise(db, php):
    # Docker archive-copy can reject read-only rootfs even for writable tmpfs.
    # Stream source files through an explicit exec into the existing /tmp tmpfs.
    package = io.BytesIO()
    with tarfile.open(fileobj=package, mode='w') as archive:
        for path in ROOT.iterdir():
            if path.is_file() and path.suffix in {'.php', '.sql', '.json'}:
                info = tarfile.TarInfo('j5/' + path.name)
                data = path.read_bytes()
                info.size = len(data)
                info.mode = 0o600
                archive.addfile(info, io.BytesIO(data))
    docker('exec', '-i', php, 'tar', '-x', '--no-same-owner', '-C', '/tmp',
           data=package.getvalue(), phase='stream_synthetic_code')
    exercise_loaded(db, php)


def exercise_loaded(db, php):
    command = ['exec', '-i', php, 'php', '-d', 'disable_functions=' + DISABLED]
    isolation = docker(*command, '/tmp/j5/isolation.php', phase='negative_connections', allowed=(0, 3), timeout=90)
    REPORT['isolation'] = json.loads(isolation.stdout)
    if not REPORT['isolation']['pass']:
        raise RuntimeError('isolation_gate_failed_no_fixtures_loaded')
    docker(*command, '-r',
           "foreach(['/var/www/html/storage/framework/views','/var/www/html/storage/framework/cache/data','/var/www/html/storage/framework/sessions','/var/www/html/storage/logs'] as $p) { if(!is_dir($p) && !mkdir($p,0700,true)) exit(2); }",
           phase='prepare_synthetic_storage')
    for filename in ('adapt.php', 'isolation.php', 'matrix.php', 'operational.php', 'probe-original.php'):
        docker(*command, '-l', '/tmp/j5/' + filename, phase='syntax_' + filename)
    adapted = docker(*command, '/tmp/j5/adapt.php', '/tmp/j5/operational.php',
                     '/tmp/j5/transaction-test.php', phase='adapt_test_guard')
    REPORT['guard_adaptation'] = json.loads(adapted.stdout)
    docker(*command, '-l', '/tmp/j5/transaction-test.php', phase='syntax_test_copy')
    matrix = docker(*command, '/tmp/j5/matrix.php', phase='synthetic_matrix', allowed=(0, 2), timeout=90)
    REPORT['matrix'] = json.loads(matrix.stdout)
    if REPORT['matrix']['result'] != 'PASS':
        raise RuntimeError('synthetic_matrix_failed')
    original = docker(*command, '/tmp/j5/original-oracle.php', phase='original_sqlite_oracle', timeout=60)
    result = json.loads(original.stdout)['data']
    REPORT['original_sqlite_oracle'] = {k: result[k] for k in (
        'sqlite_in_memory', 'fake_values_only', 'fault_rolled_back_all_writes', 'idempotent',
        'invalid_digest_rejected', 'eloquent_encryption_roundtrip', 'installed_serializer_ran')}
    if not all(REPORT['original_sqlite_oracle'].values()):
        raise RuntimeError('original_oracle_failed')
    for cid in (db, php):
        state = json.loads(docker('inspect', '--format', '{{json .State}}', cid, phase='final_state').stdout)
        if state['OOMKilled'] or not state['Running']:
            raise RuntimeError('resource_state_failed')
    REPORT['resources']['preserved_running'] = True
    REPORT['result'] = 'PASS'


def main():
    os.umask(0o077)
    name = 'configsentinel-j5-phase1-' + uuid.uuid4().hex[:10]
    private = Path.home() / '.config' / name
    private.mkdir(mode=0o700)
    REPORT['resources']['name'] = name
    REPORT['resources']['private_directory'] = str(private)
    REPORT['started_at_unix'] = time.time()
    for image in (COOLIFY, POSTGRES):
        info = json.loads(docker('image', 'inspect', image, phase='approved_image').stdout)[0]
        if info['Id'] != image:
            raise RuntimeError('image_mismatch')
        if image == COOLIFY and info['Config'].get('Volumes'):
            raise RuntimeError('unexpected_image_volumes')
    REPORT['images'] = {'coolify': COOLIFY, 'postgres': POSTGRES}
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    if int(mem['MemAvailable'].split()[0]) < 1024 * 1024:
        raise RuntimeError('insufficient_memory')
    st = os.statvfs(private)
    if st.f_bavail * st.f_frsize < 2 * 1024**3:
        raise RuntimeError('insufficient_disk')
    REPORT['capacity_gate'] = 'PASS'
    # Networking metadata only, no .Config.Env, no database or application records.
    targets = []
    for interface in json.loads(run(['ip', '-j', 'addr'], phase='host_addresses').stdout):
        for address in interface.get('addr_info', []):
            if address['family'] == 'inet' and not address['local'].startswith('127.'):
                targets.append({'class': 'host', 'ip': address['local'], 'port': 22})
    ids = docker('ps', '-q', phase='existing_container_ids').stdout.decode().split()
    for cid in ids:
        nets = json.loads(docker('inspect', '--format', '{{json .NetworkSettings.Networks}}', cid,
                                phase='existing_network_addresses').stdout)
        for net in nets.values():
            if net.get('IPAddress'):
                for port in (80, 443, 5432, 8000):
                    targets.append({'class': 'existing_service', 'ip': net['IPAddress'], 'port': port})
    if not any(x['class'] == 'host' for x in targets) or not any(x['class'] == 'existing_service' for x in targets):
        raise RuntimeError('missing_negative_target_classes')
    (ROOT / 'negative-targets.json').write_text(json.dumps(targets))
    env = private / 'synthetic.env'
    password = secrets.token_hex(32)
    key = 'base64:' + base64.b64encode(secrets.token_bytes(32)).decode()
    values = {'POSTGRES_USER': 'j5_synthetic', 'POSTGRES_DB': 'j5_synthetic',
              'POSTGRES_PASSWORD': password, 'DB_CONNECTION': 'pgsql', 'DB_HOST': name + '-db',
              'DB_PORT': '5432', 'DB_DATABASE': 'j5_synthetic', 'DB_USERNAME': 'j5_synthetic',
              'DB_PASSWORD': password, 'APP_KEY': key, 'APP_ENV': 'testing', 'APP_DEBUG': 'false',
              'LOG_CHANNEL': 'null', 'SESSION_DRIVER': 'array', 'CACHE_STORE': 'array',
              'CACHE_DRIVER': 'array', 'QUEUE_CONNECTION': 'null', 'J5_SYNTHETIC_ONLY': '1'}
    with env.open('x') as f:
        f.write(''.join(k + '=' + v + '\n' for k, v in values.items()))
    env.chmod(0o600)
    REPORT['credential_file_mode'] = oct(env.stat().st_mode & 0o777)
    label = 'configsentinel.j5.phase1=' + name
    netname = name + '-net'
    nid = docker('network', 'create', '--internal', '--ipv6=false', '--opt',
                 'com.docker.network.bridge.gateway_mode_ipv4=isolated', '--label', label,
                 netname, phase='create_network').stdout.decode().strip()
    REPORT['resources']['network_id'] = nid
    common = ['--network', netname, '--dns', '127.0.0.1', '--label', label,
              '--cpus', '0.5', '--pids-limit', '128', '--security-opt', 'no-new-privileges',
              '--cap-drop', 'ALL', '--log-driver', 'none', '--env-file', str(env)]
    db = docker('run', '-d', '--name', name + '-db', *common, '--memory', '256m',
                '--memory-swap', '256m', '--user', '70:70', '--read-only',
                '--tmpfs', '/var/lib/postgresql/data:rw,size=128m,uid=70,gid=70,mode=0700',
                '--tmpfs', '/var/run/postgresql:rw,size=4m,uid=70,gid=70',
                '--tmpfs', '/tmp:rw,size=8m', POSTGRES,
                phase='create_synthetic_postgres').stdout.decode().strip()
    REPORT['resources']['db_container_id'] = db
    php = docker('run', '-d', '--name', name + '-php', *common, '--memory', '512m',
                 '--memory-swap', '512m', '--read-only', '--tmpfs', '/tmp:rw,size=32m',
                 '--tmpfs', '/var/www/html/storage:rw,size=32m,uid=9999,gid=9999,mode=0700',
                 '--tmpfs', '/var/www/html/bootstrap/cache:rw,size=8m,uid=9999,gid=9999,mode=0700',
                 '--entrypoint', 'php', COOLIFY, '-d', 'disable_functions=' + DISABLED,
                 '-r', 'while(true){sleep(60);}', phase='create_php_cli').stdout.decode().strip()
    REPORT['resources']['php_container_id'] = php
    for _ in range(30):
        ready = docker('exec', db, 'pg_isready', '-h', '127.0.0.1', '-U', 'j5_synthetic',
                       phase='pg_isready', allowed=(0, 1, 2))
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError('postgres_not_ready')
    net = inspect_resource('network', nid)
    if not net['Internal'] or net['Options'].get('com.docker.network.bridge.gateway_mode_ipv4') != 'isolated':
        raise RuntimeError('network_not_isolated')
    if set(net['Containers']) != {db, php}:
        raise RuntimeError('unexpected_network_member')
    for cid in (db, php):
        info = json.loads(docker('inspect', cid, phase='inspect_new_resource').stdout)[0]
        if (info['HostConfig'].get('PortBindings') or info['HostConfig']['Privileged']
                or set(info['NetworkSettings']['Networks']) != {netname}
                or any(m['Type'] != 'tmpfs' for m in info['Mounts'])
                or not info['HostConfig']['ReadonlyRootfs']):
            raise RuntimeError('unexpected_resource_access')
    REPORT['static_isolation'] = {'result': 'PASS', 'network_members': 2, 'ports_published': 0,
                                  'active_mounts': 0, 'readonly_rootfs': True, 'capabilities_dropped': True}
    exercise(db, php)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Only known fixed-code RuntimeError labels; no external exception messages or outputs.
        REPORT['failure'] = {'category': type(error).__name__, 'phase': REPORT['steps'][-1]['phase'] if REPORT['steps'] else 'preflight',
                             'code': str(error) if type(error) is RuntimeError else 'unexpected_exception'}
    REPORT['duration_seconds'] = round(time.time() - REPORT.get('started_at_unix', time.time()), 3)
    print(json.dumps(REPORT, indent=2))
    raise SystemExit(0 if REPORT['result'] == 'PASS' else 2)
