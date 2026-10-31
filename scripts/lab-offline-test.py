#!/usr/bin/env python3
"""Authorized synthetic pilot only. Never modifies the host network/firewall."""
import json,subprocess,time
from pathlib import Path
image='alpine:3.23@sha256:ff7f0c727dd796aa36787bfcd9a64bf35a6ce72a73451b3359fde849b6703d63'
def ssh(cmd):return subprocess.check_output(['ssh','frank-note2',cmd],text=True).strip()
def fixture(command):return ssh(f"docker run --rm --mount type=volume,src=configsentinel-lab-fixtures,dst=/fixtures {image} sh -ec '{command}'")
def config(command):return ssh(f"docker run --rm --mount type=volume,src=configsentinel-lab-config,dst=/config {image} sh -ec '{command}'")
def snapshot(label):
 ssh('docker stop configsentinel-agent-lab >/dev/null; mkdir -p /home/franklin/apps/configsentinel-lab/evidence/'+label+'; chmod 700 /home/franklin/apps/configsentinel-lab/evidence; docker cp configsentinel-agent-lab:/state/. /home/franklin/apps/configsentinel-lab/evidence/'+label+'/')
 code="import sqlite3,json; c=sqlite3.connect('/home/franklin/apps/configsentinel-lab/evidence/"+label+"/events.sqlite'); print(json.dumps({'count':c.execute('select count(*) from events').fetchone()[0],'ids':[r[0] for r in c.execute('select uuid from events order by seq')]}))"
 import shlex
 return json.loads(ssh('python3 -c '+shlex.quote(code)))
start=time.time()
config('cp /config/agent.yaml /config/agent.online.yaml; sed -i "s#https://configsentinel-dev.franklem.uk/api/v1#https://127.0.0.1:1/api/v1#" /config/agent.yaml')
ssh('docker restart configsentinel-agent-lab >/dev/null');time.sleep(6)
fixture('printf "synthetic=true\\nrevision=2\\n" > /fixtures/demo.conf');time.sleep(7)
fixture('rm /fixtures/demo.conf');time.sleep(7)
fixture('printf "synthetic=true\\nrevision=3\\n" > /fixtures/demo.conf');time.sleep(7)
before=snapshot('offline-before-restart');assert before['count']>=3,before
ssh('docker start configsentinel-agent-lab >/dev/null');time.sleep(7)
after=snapshot('offline-after-restart');assert before['ids']==after['ids'],(before,after)
ssh('docker start configsentinel-agent-lab >/dev/null')
while time.time()-start<90:time.sleep(5)
config('cp /config/agent.online.yaml /config/agent.yaml; chmod 644 /config/agent.yaml')
ssh('docker restart configsentinel-agent-lab >/dev/null');time.sleep(12)
recovered=snapshot('online-recovered');ssh('docker start configsentinel-agent-lab >/dev/null');assert recovered['count']==0,recovered
result={'offline_seconds':round(time.time()-start),'persisted_events':before['count'],'restart_preserved_ids':True,'pending_after_recovery':recovered['count']}
Path('.local/offline-evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
