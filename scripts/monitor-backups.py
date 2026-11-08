#!/usr/bin/env python3
"""Independent backup probe and scoped Kuma push; never logs credential URLs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import urllib.parse
import urllib.request


def notify(url, report):
    parsed = urllib.parse.urlsplit(url)
    trusted = (parsed.scheme=='https' and parsed.netloc=='status.franklem.uk') or (parsed.scheme=='http' and parsed.netloc=='127.0.0.1:3001')
    if not trusted or not parsed.path.startswith('/api/push/') or parsed.query or parsed.fragment:
        raise ValueError('invalid monitor destination')
    query = urllib.parse.urlencode({'status':'up' if report['status']=='ok' else 'down',
                                   'msg':'backup verified' if report['status']=='ok' else report.get('reason','backup check failed')})
    with urllib.request.urlopen(url+'?'+query, timeout=15) as response:
        body = json.load(response)
        if response.status != 200 or body.get('ok') is not True:
            raise ValueError('monitor rejected status')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=Path.home()/'.local/share/configsentinel-backups')
    parser.add_argument('--config',type=Path,default=Path.home()/'.config/configsentinel-backup')
    parser.add_argument('--service-name',type=str,default='configsentinel-backup.service')
    args=parser.parse_args()
    probe=Path(__file__).with_name('check-backup-health.py')
    try:
        result=subprocess.run([sys.executable,str(probe),'--base',str(args.base),'--check-systemd','--service-name',args.service_name],capture_output=True,text=True,timeout=30)
        report=json.loads(result.stdout)
        if report['status']=='ok':
            key=args.config/'encryption.key'
            if key.is_symlink() or key.stat().st_mode & 0o077 or key.stat().st_uid!=os.geteuid():
                raise ValueError('unsafe key')
            filename=(args.base/'last-success.txt').read_text().strip().split()[1]
            decrypted=subprocess.run(['gpg','--batch','--pinentry-mode','loopback','--passphrase-file',str(key),'--decrypt',str(args.base/'daily'/filename)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90)
            if decrypted.returncode:
                report={'status':'error','reason':'backup_decryption_failed'}
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):
        report={'status':'error','reason':'backup_verification_failed'}
    try:
        destination=args.config/'monitor-url'
        if destination.is_symlink() or destination.stat().st_mode & 0o077:
            raise ValueError('unsafe monitor configuration')
        notify(destination.read_text().strip(),report)
    except Exception:
        # urllib exceptions can include secret paths; never print exception text.
        print(json.dumps({'status':'error','reason':'monitor_delivery_failed'}))
        return 2
    print(json.dumps(report))
    return 0 if report['status']=='ok' else 2


if __name__=='__main__':raise SystemExit(main())
