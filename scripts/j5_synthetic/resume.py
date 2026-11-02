#!/usr/bin/env python3
"""Upload revised harness code and explicitly continue inventoried synthetic IDs."""
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

root = Path(__file__).resolve().parents[2]
here = Path(__file__).resolve().parent
previous = Path(sys.argv[1])
output = Path(sys.argv[2])
if output.exists():
    raise SystemExit('Refusing to overwrite previous evidence')
context = json.loads(previous.read_text())
remote = context['resources']['code_directory']
if not re.fullmatch(r'/home/franklin/\.config/configsentinel-j5-phase1-code-[a-f0-9]{10}', remote):
    raise SystemExit('Unexpected staging path')
files = {p.name:p.read_bytes() for p in here.iterdir() if p.is_file() and p.suffix in {'.php','.py','.sql'}}
files['resume-state.json'] = json.dumps(context).encode()
package = io.BytesIO()
with tarfile.open(fileobj=package,mode='w') as tar:
    for name,data in files.items():
        entry=tarfile.TarInfo(name);entry.size=len(data);entry.mode=0o600
        tar.addfile(entry,io.BytesIO(data))
r=subprocess.run(['ssh','-o','BatchMode=yes','contabo','tar -x --no-same-owner -C '+shlex.quote(remote)],input=package.getvalue(),capture_output=True,timeout=60)
if r.returncode or r.stderr:raise SystemExit('Harness upload failed; raw output withheld')
r=subprocess.run(['ssh','-o','BatchMode=yes','contabo','python3 '+shlex.quote(remote+'/continue.py')],capture_output=True,timeout=240)
if r.stderr:raise SystemExit('Continuation stderr withheld')
try:result=json.loads(r.stdout)
except (ValueError,UnicodeError):raise SystemExit('Invalid continuation response; raw output withheld') from None
result['package_sha256'].update({name:hashlib.sha256(data).hexdigest() for name,data in files.items() if name!='resume-state.json'})
output.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'report':str(output),'resources_preserved':True}))
raise SystemExit(0 if result['result']=='PASS' else 2)
