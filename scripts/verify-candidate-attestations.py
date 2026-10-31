#!/usr/bin/env python3
"""Check digest/commit claims after Cosign has verified the pinned public key."""
import base64
import json
import os
from pathlib import Path

base=Path('.local/candidate-artifact')
record=json.loads((base/'image.json').read_text())
decoder=json.JSONDecoder()
remaining=(base/'verified-provenance.json').read_text().strip()
statements=[]
while remaining:
    value,end=decoder.raw_decode(remaining)
    for item in value if isinstance(value,list) else [value]:
        statements.append(json.loads(base64.b64decode(item['payload'])))
    remaining=remaining[end:].strip()
digest=record['image'].split('@sha256:')[1]
assert any(s['predicate']['buildDefinition']['externalParameters']['commit']==os.environ['GITHUB_SHA'] and
           any(v['digest'].get('sha256')==digest for v in s['subject']) for s in statements), 'Signed source/digest mismatch'
record['provenance_verified']=True
record['signature_verified']=True
record['signature_policy']='pinned repository public key; private registry; no public transparency log'
(base/'image.json').write_text(json.dumps(record,indent=2)+'\n')
