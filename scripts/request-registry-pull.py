#!/usr/bin/env python3
"""CI client: send a short-lived package token over pinned, restricted SSH."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path)
    args=parser.parse_args()
    if args.manifest:
        manifest=json.loads(args.manifest.read_text())
        records=[manifest[c] for c in ['api','web','db','agent']]
    else:
        records=[json.loads(p.read_text()) for p in Path('.local/registry').glob('**/image.json')]
    if len(records)!=4:raise SystemExit('Four scanned image records required')
    with tempfile.TemporaryDirectory() as folder:
        key=Path(folder)/'identity';key.write_text(os.environ['PULL_SSH_KEY'].strip()+'\n');key.chmod(0o600)
        payload=json.dumps({'token':os.environ['GITHUB_TOKEN'],'images':[v['image'] for v in records]})
        subprocess.run(['ssh','-T','-i',str(key),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=.github/contabo-known-hosts','franklin@158.220.120.2'],input=payload,text=True,check=True,timeout=750)


if __name__=='__main__':main()
