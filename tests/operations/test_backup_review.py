"""Exercise the unchanged backup program only in synthetic temporary directories."""
import io
from pathlib import Path
import runpy
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/offsite-backup.py'

class BackupReview(unittest.TestCase):
    def test_transport_failure_preserves_previous_backup_and_marker(self):
        with tempfile.TemporaryDirectory(prefix='configsentinel-backup-review-') as folder:
            home = Path(folder)
            base = home / '.local/share/configsentinel-backups'
            (base / 'daily').mkdir(parents=True)
            previous = base / 'daily/2000-01-01.dump.gpg'
            previous.write_bytes(b'synthetic-encrypted-backup')
            marker = base / 'last-success.txt'
            marker.write_text('2000-01-01T00:00:00+00:00 previous.dump.gpg\n')
            fake_ssh = types.SimpleNamespace(stdout=io.BytesIO(b''), stderr=io.BytesIO(b'fixture transport failure'), wait=lambda: 255)
            def fake_gpg(args, **kwargs):
                Path(args[args.index('--output')+1]).write_bytes(b'synthetic-partial')
                return types.SimpleNamespace(returncode=0)
            with patch('pathlib.Path.home', return_value=home), patch('subprocess.Popen', return_value=fake_ssh), patch('subprocess.run', side_effect=fake_gpg):
                with self.assertRaisesRegex(RuntimeError, 'pipeline failed'):
                    runpy.run_path(str(SCRIPT), run_name='__main__')
            self.assertEqual(previous.read_bytes(), b'synthetic-encrypted-backup')
            self.assertTrue(marker.read_text().startswith('2000-01-01'))
            self.assertFalse(list((base / 'daily').glob('.pending-*')))
            self.assertFalse((base / 'last-failure.txt').exists())  # Characterization: no failure/age monitor is emitted.


class BackupHealthProbe(unittest.TestCase):
    def test_health_age_checksum_and_service_status(self):
        import datetime as dt
        import hashlib
        module = runpy.run_path(str(SCRIPT.parent/'check-backup-health.py'))
        check = module['check']
        now=dt.datetime(2026,10,31,18,0,tzinfo=dt.timezone.utc)
        with tempfile.TemporaryDirectory(prefix='configsentinel-backup-probe-') as folder:
            base=Path(folder);(base/'daily').mkdir()
            self.assertEqual(check(base,now=now)['status'],'error')
            dump=base/'daily/2026-10-31.dump.gpg';dump.write_bytes(b'synthetic encrypted fixture'*100)
            dump.with_suffix('.gpg.sha256').write_text(hashlib.sha256(dump.read_bytes()).hexdigest()+'  '+dump.name+'\n')
            marker=base/'last-success.txt';marker.write_text(now.isoformat()+' '+dump.name+'\n')
            self.assertEqual(check(base,now=now)['status'],'ok')
            self.assertEqual(check(base,now=now+dt.timedelta(hours=27))['reason'],'backup_overdue')
            self.assertEqual(check(base,now=now,service_result='exit-code')['reason'],'backup_service_failed')
            dump.write_bytes(b'corrupt synthetic encrypted fixture'*100)
            self.assertEqual(check(base,now=now)['reason'],'checksum_mismatch')

if __name__ == '__main__':
    unittest.main()
