#!/usr/bin/env python3
"""Local operator helper. Token read from ignored .local/coolify.token, never logged."""
import json,sys,urllib.request,urllib.error
from pathlib import Path
base='https://coolify.franklem.uk/api/v1'
method,path=sys.argv[1:3]
body=Path(sys.argv[3]).read_bytes() if len(sys.argv)>3 else None
req=urllib.request.Request(base+path,data=body,method=method,headers={'Authorization':'Bearer '+Path('.local/coolify.token').read_text().strip(),'Content-Type':'application/json','Accept':'application/json'})
try:
 with urllib.request.urlopen(req,timeout=60) as res: print(res.read().decode())
except urllib.error.HTTPError as e:
 print(e.code,e.read().decode(),file=sys.stderr);sys.exit(1)
