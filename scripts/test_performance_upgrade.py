#!/usr/bin/env python3
"""Test reviewed digest swap and fallback in isolated SQLite and PostgreSQL."""
import json
from pathlib import Path
import subprocess
import re
root=Path(__file__).resolve().parent
def get(name):
 s=(root/name).read_text()
 if not s.startswith('<?php\n'):raise RuntimeError('invalid fixture')
 return s
def ssh(command,source=None):
 r=subprocess.run(['ssh','-o','BatchMode=yes','contabo',command],input=source,text=True,capture_output=True,timeout=90)
 if r.returncode or r.stderr:raise RuntimeError(f'fixture failure exit={r.returncode} stdout_bytes={len(r.stdout)} stderr_bytes={len(r.stderr)}')
 return r.stdout
j5=get('j5_coolify_transaction.php');probe=get('probe_j5_isolated.php');web=get('web_digest_upgrade.php');webtest=get('test_web_digest_upgrade.php');api=get('api_digest_upgrade.php');apitest=get('test_api_digest_upgrade.php');cap=get('capacity_digest_upgrade.php');test=get('test_performance_upgrade.php');perf=get('performance_digest_upgrade.php')
marker='use Illuminate\\Support\\Facades\\DB;\n';assert probe.count(marker)==webtest.count(marker)==1
src=j5+'\nob_start();\n'+probe[6:]+'\nob_end_clean();\n'+web[6:]+'\nob_start();\n'+webtest.split(marker,1)[1]+'\nob_end_clean();\n'+api[6:]+'\nob_start();\n'+apitest[6:]+'\nob_end_clean();\n'+cap[6:]+'\n'+"configsentinel_capacity_upgrade(['mode'=>'isolated','uuid'=>'configsentinel-j5-isolated','direction'=>'forward']);\n"+perf[6:]+'\n'+test[6:]
sqlite=json.loads(ssh('docker exec -i coolify php',src))
fixture=json.loads((root.parent/'docs/evidence/capacity-j5-fixture-20261104/result.json').read_text())
prefix=fixture['resources']['name']
if not re.fullmatch(r'configsentinel-j5-phase1-[a-f0-9]{10}',prefix):raise RuntimeError('invalid fixture name')
name=prefix+'-php';net=prefix+'-net';x=json.loads(ssh('docker inspect '+name))[0]
if not x['State']['Running'] or not x['HostConfig']['ReadonlyRootfs'] or x['HostConfig']['PortBindings'] or set(x['NetworkSettings']['Networks'])!={net} or not json.loads(ssh('docker network inspect '+net))[0]['Internal']:raise RuntimeError('fixture isolation changed')
wpg=get('test_web_digest_upgrade_pg.php');apg=get('test_api_digest_upgrade_pg.php');cpg=get('test_performance_upgrade_pg.php')
src=web+'\nob_start();\n'+wpg[6:]+'\nob_end_clean();\n'+api[6:]+'\nob_start();\n'+apg[6:]+'\nob_end_clean();\n'+cap[6:]+'\n'+"configsentinel_capacity_upgrade(['mode'=>'active','uuid'=>'oi6lvzwzomwtbbgzf5uzofuh','direction'=>'forward']);\n"+perf[6:]+'\n'+cpg[6:]
postgres=json.loads(ssh('docker exec -i '+name+' php -d disable_functions=exec,system,passthru,shell_exec,proc_open,popen,pcntl_exec',src))
for r in (sqlite,postgres):
 if any(r.get(k)!='PASS' for k in ('update','rollback','queue_guard','idempotence','fallback')):raise RuntimeError('test failure')
print(json.dumps({'sqlite':sqlite,'postgres':postgres},indent=2))
