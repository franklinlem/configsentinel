#!/usr/bin/env python3
"""Package source-only synthetic harness over SSH, without active metadata access."""
import hashlib
import io
import json
import pathlib
import shlex
import subprocess
import tarfile
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
EVIDENCE = ROOT / 'docs/evidence/capacity-j5-fixture-20261104'
files = {p.name: p.read_bytes() for p in HERE.iterdir() if p.is_file() and p.suffix in {'.php', '.py', '.sql'}}
files['operational.php'] = (ROOT / 'scripts/j5_coolify_transaction.php').read_bytes()
files['probe-original.php'] = (ROOT / 'scripts/probe_j5_isolated.php').read_bytes()
files['original-oracle.php'] = b"<?php require '/tmp/j5/operational.php'; require '/tmp/j5/probe-original.php';\n"
files['candidate.json'] = (ROOT / 'deploy/release-manifest.candidate.json').read_bytes()
files['fallback.json'] = (ROOT / 'deploy/release-manifest.fallback.json').read_bytes()
package = io.BytesIO()
with tarfile.open(fileobj=package, mode='w') as archive:
    for name, data in files.items():
        entry = tarfile.TarInfo(name)
        entry.size = len(data)
        entry.mode = 0o600
        archive.addfile(entry, io.BytesIO(data))
stage = 'configsentinel-j5-phase1-code-' + uuid.uuid4().hex[:10]
extractor = '''import io,pathlib,sys,tarfile,os
os.umask(0o077)
p=pathlib.Path.home()/'.config'/sys.argv[1];p.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(sys.stdin.buffer.read())) as t:
 for m in t.getmembers():
  if not m.isfile() or pathlib.Path(m.name).name!=m.name:raise RuntimeError('invalid_package')
  (p/m.name).write_bytes(t.extractfile(m).read())
print(str(p))
'''
r = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'contabo', 'python3 -c ' + shlex.quote(extractor) + ' ' + shlex.quote(stage)],
                   input=package.getvalue(), capture_output=True, timeout=90)
if r.returncode or r.stderr:
    raise SystemExit('Package transport failed; raw output withheld')
remote_path = r.stdout.decode().strip()
if remote_path != '/home/franklin/.config/' + stage:
    raise SystemExit('Unexpected private staging path')
r = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'contabo', 'python3 ' + shlex.quote(remote_path + '/run.py')],
                   capture_output=True, timeout=300)
if r.stderr:
    raise SystemExit('Remote diagnostic emitted unexpected stderr; raw output withheld')
try:
    result = json.loads(r.stdout)
except (ValueError, UnicodeError):
    raise SystemExit('Remote diagnostic invalid envelope; raw output withheld') from None
result['package_sha256'] = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
result['resources']['code_directory'] = remote_path
EVIDENCE.mkdir(parents=True, exist_ok=True)
path = EVIDENCE / 'result.json'
if path.exists():
    raise SystemExit('Refusing to overwrite a previous attempt result')
path.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'result': result['result'], 'report': str(path), 'resources_preserved': True}))
raise SystemExit(0 if result['result'] == 'PASS' else 2)
