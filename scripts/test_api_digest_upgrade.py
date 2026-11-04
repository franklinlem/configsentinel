#!/usr/bin/env python3
"""Test digest transaction with Coolify models, synthetic SQLite and PostgreSQL."""
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parent
def read(name):
    s=(root/name).read_text()
    if not s.startswith('<?php\n'): raise RuntimeError('invalid PHP source')
    return s

def ssh(command, source=None):
    r=subprocess.run(['ssh','-o','BatchMode=yes','contabo',command], input=source, text=True, capture_output=True, timeout=90)
    if r.returncode or r.stderr: raise RuntimeError(f'probe failure: exit={r.returncode} stdout_bytes={len(r.stdout)} stderr_bytes={len(r.stderr)}')
    return r.stdout

j5=read('j5_coolify_transaction.php');probe=read('probe_j5_isolated.php');web=read('web_digest_upgrade.php');webtest=read('test_web_digest_upgrade.php');api=read('api_digest_upgrade.php');apitest=read('test_api_digest_upgrade.php')
marker='use Illuminate\\Support\\Facades\\DB;\n'
if probe.count(marker)!=1 or webtest.count(marker)!=1: raise RuntimeError('fixture structure changed')
source=j5+'\nob_start();\n'+probe[6:]+'\nob_end_clean();\n'+web[6:]+'\nob_start();\n'+webtest.split(marker,1)[1]+'\nob_end_clean();\n'+api[6:]+'\n'+apitest[6:]
sqlite=json.loads(ssh('docker exec -i coolify php',source))
name='configsentinel-j5-phase1-f72ab6b2a2-php';net='configsentinel-j5-phase1-f72ab6b2a2-net'
x=json.loads(ssh('docker inspect '+name))[0]
if not x['State']['Running'] or not x['HostConfig']['ReadonlyRootfs'] or x['HostConfig']['PortBindings'] or set(x['NetworkSettings']['Networks'])!={net}: raise RuntimeError('container isolation changed')
if not json.loads(ssh('docker network inspect '+net))[0]['Internal']: raise RuntimeError('network isolation changed')
pgtest=read('test_web_digest_upgrade_pg.php');apipg=read('test_api_digest_upgrade_pg.php')
source=web+'\nob_start();\n'+pgtest[6:]+'\nob_end_clean();\n'+api[6:]+'\n'+apipg[6:]
postgres=json.loads(ssh('docker exec -i '+name+' php -d disable_functions=exec,system,passthru,shell_exec,proc_open,popen,pcntl_exec',source))
for result in (sqlite,postgres):
    if any(result.get(k)!='PASS' for k in ('rollback','queue_guard','update','idempotence')): raise RuntimeError('test failure')
print(json.dumps({'sqlite':sqlite,'postgres':postgres},indent=2))
