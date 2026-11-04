#!/usr/bin/env python3
"""Run web-upgrade tests using Coolify models and a SQLite in-memory database."""
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent
helper = (root / 'j5_coolify_transaction.php').read_text()
probe = (root / 'probe_j5_isolated.php').read_text()
web = (root / 'web_digest_upgrade.php').read_text()
test = (root / 'test_web_digest_upgrade.php').read_text()
assert all(source.startswith('<?php\n') for source in (helper, probe, web, test))
marker = 'use Illuminate\\Support\\Facades\\DB;\n'
assert probe.count(marker) == test.count(marker) == 1
source = helper + '\nob_start();\n' + probe[6:] + '\nob_end_clean();\n' + web[6:] + '\n' + test.split(marker, 1)[1]
r = subprocess.run(['ssh', '-o', 'BatchMode=yes', 'contabo', 'docker exec -i coolify php'], input=source, text=True, capture_output=True, timeout=60)
if r.returncode or r.stderr:
    raise SystemExit(f'synthetic probe failed: exit={r.returncode}, stdout_bytes={len(r.stdout)}, stderr_bytes={len(r.stderr)}')
result = json.loads(r.stdout)
if any(result.get(key) != 'PASS' for key in ('rollback', 'invalid_digest', 'queue_guard', 'update', 'idempotence')):
    raise SystemExit('synthetic probe reported failure')
print(json.dumps(result, indent=2))
