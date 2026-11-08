"""Real process/lock/deadline checks use only synthetic temporary paths."""
import datetime as dt
import fcntl
import hashlib
from pathlib import Path
import runpy
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS=Path(__file__).resolve().parents[2]/'scripts'
backup=runpy.run_path(str(SCRIPTS/'offsite-backup.py'))
check=runpy.run_path(str(SCRIPTS/'check-backup-health.py'))['check']


class BackupReview(unittest.TestCase):
    def test_success_preserves_all_existing_recovery_points(self):
        with tempfile.TemporaryDirectory(prefix='configsentinel-backup-retention-') as folder:
            base=Path(folder)/'backup';config=Path(folder)/'config';config.mkdir();(base/'daily').mkdir(parents=True);(base/'weekly').mkdir()
            key=config/'encryption.key';key.write_text('synthetic fixture '*4);key.chmod(0o600)
            existing=[]
            for day in range(1,10):
                p=base/'daily'/f'2026-01-{day:02d}T000000000000Z.dump.gpg';p.write_bytes(b'old synthetic point');existing.append(p)
            for week in range(1,6):
                p=base/'weekly'/f'2026-W{week:02d}.dump.gpg';p.write_bytes(b'old synthetic point');existing.append(p)
            original=subprocess.Popen
            def synthetic_pipeline(command, **kwargs):
                if command[0]=='ssh':
                    return original(['python3','-c','import sys;sys.stdout.buffer.write(b"x"*2048)'],**kwargs)
                target=command[command.index('--output')+1]
                return original(['python3','-c','import sys;open(sys.argv[1],"wb").write(sys.stdin.buffer.read())',target],**kwargs)
            with patch('subprocess.Popen',side_effect=synthetic_pipeline):
                new=backup['perform_backup'](base,config)
            self.assertTrue(new.is_file())
            self.assertTrue(all(p.read_bytes()==b'old synthetic point' for p in existing))

    def test_fail_closed_lock_timeout_and_previous_backup(self):
        with tempfile.TemporaryDirectory(prefix='configsentinel-backup-review-') as folder:
            base=Path(folder)/'backup';base.mkdir();config=Path(folder)/'config';config.mkdir()
            marker=base/'last-success.txt';marker.write_text('previous recovery point')
            with self.assertRaises(RuntimeError):backup['perform_backup'](base,config)
            self.assertFalse((config/'encryption.key').exists())
            key=config/'encryption.key';key.write_text('synthetic fixture '*4);key.chmod(0o600)
            with (base/'.backup.lock').open('w') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with self.assertRaisesRegex(RuntimeError,'already running'):
                    backup['perform_backup'](base,config)
            fake=Path(folder)/'process.py'
            fake.write_text('import time; time.sleep(20)')
            original=subprocess.Popen
            def sleeping(*args,**kwargs):
                return original(['python3',str(fake)],**kwargs)
            start=time.monotonic()
            with patch('subprocess.Popen',side_effect=sleeping):
                with self.assertRaisesRegex(RuntimeError,'deadline'):
                    backup['perform_backup'](base,config,timeout=0.1)
            self.assertLess(time.monotonic()-start,3)
            self.assertEqual(marker.read_text(),'previous recovery point')
            self.assertFalse(list(base.glob('daily/.pending-*')))
            def failing(*args,**kwargs):
                return original(['python3','-c','raise SystemExit(255)'],**kwargs)
            with patch('subprocess.Popen',side_effect=failing):
                with self.assertRaisesRegex(RuntimeError,'pipeline failed'):
                    backup['perform_backup'](base,config)
            self.assertEqual(marker.read_text(),'previous recovery point')


class BackupHealthProbe(unittest.TestCase):
    def test_health_age_checksum_and_service_status(self):
        now=dt.datetime(2026,10,31,18,0,tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);(base/'daily').mkdir()
            self.assertEqual(check(base,now=now)['status'],'error')
            dump=base/'daily/2026-10-31T180000000001Z.dump.gpg';dump.write_bytes(b'synthetic encrypted fixture'*100)
            dump.with_suffix('.gpg.sha256').write_text(hashlib.sha256(dump.read_bytes()).hexdigest()+'  '+dump.name+'\n')
            marker=base/'last-success.txt';marker.write_text(now.isoformat()+' '+dump.name+'\n')
            self.assertEqual(check(base,now=now)['status'],'ok')
            from collections import namedtuple
            disk=namedtuple('disk', ['total','used','free'])
            with patch('shutil.disk_usage',return_value=disk(100*(1<<30), 99*(1<<30), 1<<30)):
                self.assertEqual(check(base,now=now)['reason'],'backup_low_space')
            with patch('shutil.disk_usage',return_value=disk(10*(1<<30), 10*(1<<30)-(512<<20), 512<<20)):
                self.assertEqual(check(base,now=now)['reason'],'backup_low_space')
            self.assertEqual(check(base,now=now+dt.timedelta(hours=27))['reason'],'backup_overdue')
            self.assertEqual(check(base,now=now,service_result='exit-code')['reason'],'backup_service_failed')
            dump.write_bytes(b'corrupt synthetic encrypted fixture'*100)
            self.assertEqual(check(base,now=now)['reason'],'checksum_mismatch')


class MonitorDelivery(unittest.TestCase):
    def test_up_down_delivery_and_secret_url_redaction(self):
        import json
        import io
        notify=runpy.run_path(str(SCRIPTS/'monitor-backups.py'))['notify']
        class Reply(io.BytesIO):status=200
        def reply(*args,**kwargs):return Reply(json.dumps({'ok':True}).encode())
        with patch('urllib.request.urlopen',side_effect=reply) as request:
            for status in ['ok','error']:
                notify('https://status.franklem.uk/api/push/synthetic-monitor',{'status':status,'reason':'backup_overdue'})
            self.assertIn('status=up',request.call_args_list[0].args[0])
            self.assertIn('status=down',request.call_args_list[1].args[0])
        with self.assertRaises(ValueError):notify('http://elsewhere/api/push/synthetic',{'status':'ok'})
