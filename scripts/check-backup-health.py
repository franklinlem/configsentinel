#!/usr/bin/env python3
"""Read-only probe. Prints no key, dump content, credential or subprocess output."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess


def check(base, max_age_hours=26, now=None, service_result='success'):
    now = now or dt.datetime.now(dt.timezone.utc)
    def fail(reason, **extra):return {'status':'error','reason':reason,**extra}
    if service_result not in ('success', ''):return fail('backup_service_failed')
    try:
        stamp, filename = (base/'last-success.txt').read_text().strip().split()
        observed = dt.datetime.fromisoformat(stamp)
        if observed.tzinfo is None:return fail('marker_timezone_missing')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}\.dump\.gpg', filename):return fail('invalid_backup_filename')
        age=(now-observed).total_seconds()
        if age < -300:return fail('marker_in_future')
        if age > max_age_hours*3600:return fail('backup_overdue',age_seconds=round(age))
        backup=base/'daily'/filename
        if backup.is_symlink() or backup.stat().st_size<1024:return fail('backup_missing_or_invalid')
        checksum=backup.with_suffix(backup.suffix+'.sha256').read_text().split()[0]
        with backup.open('rb') as stream:
            digest=hashlib.file_digest(stream,'sha256').hexdigest()
        if not re.fullmatch('[a-f0-9]{64}',checksum) or digest!=checksum:return fail('checksum_mismatch')
        return {'status':'ok','age_seconds':round(age),'checksum':'verified'}
    except (OSError,ValueError,IndexError):return fail('backup_metadata_unavailable')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=Path.home()/'.local/share/configsentinel-backups')
    parser.add_argument('--max-age-hours',type=float,default=26)
    parser.add_argument('--check-systemd',action='store_true')
    args=parser.parse_args()
    if args.max_age_hours<=0:parser.error('positive age required')
    result='success'
    if args.check_systemd:
        try:
            response=subprocess.run(['systemctl','--user','show','configsentinel-backup.service','--property=Result','--value'],capture_output=True,text=True,timeout=5)
            result=response.stdout.strip() if response.returncode==0 else 'unavailable'
        except (OSError,subprocess.TimeoutExpired):result='unavailable'
    report=check(args.base,args.max_age_hours,service_result=result)
    print(json.dumps(report));return 0 if report['status']=='ok' else 2

if __name__=='__main__':raise SystemExit(main())
