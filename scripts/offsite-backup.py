#!/usr/bin/env python3
"""Bounded, locked encrypted pull. Existing key provisioning is mandatory."""
import argparse
import datetime as dt
import fcntl
import hashlib
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import tempfile
import time


def atomic_write(path, content):
    fd, temporary = tempfile.mkstemp(prefix='.metadata-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def checksum(path):
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    atomic_write(path.with_suffix(path.suffix+'.sha256'), digest+'  '+path.name+'\n')


def perform_backup(base, config, timeout=300):
    os.umask(0o077)
    base.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(base/'.backup.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(lock_fd, 'w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Backup already running') from None
        key = config/'encryption.key'
        try:
            info = key.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid() or info.st_size < 32:
                raise RuntimeError('Backup key unavailable or unsafe')
        except OSError:
            raise RuntimeError('Backup key unavailable or unsafe') from None
        daily, weekly = base/'daily', base/'weekly'
        daily.mkdir(exist_ok=True); weekly.mkdir(exist_ok=True)
        now = dt.datetime.now(dt.timezone.utc)
        # Never replace an existing same-day recovery point.
        final = daily/(now.strftime('%Y-%m-%dT%H%M%S%fZ')+'.dump.gpg')
        fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=daily)
        os.close(fd)
        children = []
        deadline = time.monotonic()+timeout
        try:
            with tempfile.TemporaryFile() as errors:
                ssh = subprocess.Popen([
                    'ssh','-T','-i',str(config/'id_ed25519'),
                    '-o','IdentitiesOnly=yes','-o','BatchMode=yes',
                    '-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15',
                    '-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2',
                    '-o','UserKnownHostsFile='+str(config/'known_hosts'),
                    'franklin@158.220.120.2',
                ], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=errors, start_new_session=True)
                children.append(ssh)
                gpg = subprocess.Popen([
                    'gpg','--batch','--yes','--pinentry-mode','loopback',
                    '--passphrase-file',str(key),'--symmetric','--cipher-algo','AES256',
                    '--output',temporary,
                ], stdin=ssh.stdout, stdout=subprocess.DEVNULL, stderr=errors, start_new_session=True)
                children.append(gpg)
                ssh.stdout.close()
                gpg_code = gpg.wait(timeout=max(0.01, deadline-time.monotonic()))
                ssh_code = ssh.wait(timeout=max(0.01, deadline-time.monotonic()))
                if gpg_code or ssh_code:
                    raise RuntimeError('Encrypted backup pipeline failed; previous backups preserved')
            if Path(temporary).stat().st_size < 1024:
                raise RuntimeError('Encrypted backup too small')
            with open(temporary,'rb') as stream:
                os.fsync(stream.fileno())
            os.rename(temporary, final)
            checksum(final)
            week = weekly/(now.strftime('%G-W%V')+'.dump.gpg')
            if not week.exists():
                weekly_fd, weekly_temporary = tempfile.mkstemp(prefix='.pending-week-', dir=weekly)
                try:
                    with os.fdopen(weekly_fd, 'wb') as destination, final.open('rb') as source:
                        shutil.copyfileobj(source, destination)
                        destination.flush()
                        os.fsync(destination.fileno())
                    # Publish only a complete copy and never replace an existing point.
                    os.link(weekly_temporary, week)
                finally:
                    Path(weekly_temporary).unlink(missing_ok=True)
                checksum(week)
            atomic_write(base/'last-success.txt', now.isoformat()+' '+final.name+'\n')
            # Preserve all existing recovery points until a retention policy
            # and deletion procedure have been explicitly approved.
            return final
        except subprocess.TimeoutExpired:
            raise RuntimeError('Encrypted backup deadline exceeded; previous backups preserved') from None
        finally:
            for child in children:
                if child.poll() is None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
            Path(temporary).unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path.home()/'.local/share/configsentinel-backups')
    parser.add_argument('--config', type=Path, default=Path.home()/'.config/configsentinel-backup')
    parser.add_argument('--timeout-seconds', type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.timeout_seconds <= 300:
        parser.error('timeout must be between 1 and 300 seconds')
    try:
        perform_backup(args.base, args.config, args.timeout_seconds)
    except (OSError, RuntimeError):
        print('ConfigSentinel backup failed; previous recovery points preserved')
        return 2
    print('ConfigSentinel encrypted offsite backup complete')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
