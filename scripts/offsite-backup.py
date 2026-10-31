#!/usr/bin/env python3
"""Daily encrypted pull via a single-purpose forced-command SSH key."""
import datetime,hashlib,os,secrets,shutil,subprocess,tempfile
from pathlib import Path
os.umask(0o077)
base=Path.home()/'.local/share/configsentinel-backups'
config=Path.home()/'.config/configsentinel-backup'
base.mkdir(parents=True,exist_ok=True);config.mkdir(parents=True,exist_ok=True)
key=config/'encryption.key'
if not key.exists():key.write_text(secrets.token_urlsafe(48));key.chmod(0o600)
now=datetime.datetime.now(datetime.timezone.utc)
daily=base/'daily';weekly=base/'weekly';daily.mkdir(exist_ok=True);weekly.mkdir(exist_ok=True)
final=daily/(now.strftime('%Y-%m-%d')+'.dump.gpg')
fd,tmp=tempfile.mkstemp(prefix='.pending-',dir=daily);os.close(fd)
try:
 ssh=subprocess.Popen(['ssh','-T','-i',str(config/'id_ed25519'),'-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(config/'known_hosts'),'franklin@158.220.120.2'],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 gpg=subprocess.run(['gpg','--batch','--yes','--pinentry-mode','loopback','--passphrase-file',str(key),'--symmetric','--cipher-algo','AES256','--output',tmp],stdin=ssh.stdout,capture_output=True)
 ssh.stdout.close();ssh_error=ssh.stderr.read();returncode=ssh.wait()
 if returncode or gpg.returncode:raise RuntimeError('Encrypted backup pipeline failed; previous backups preserved')
 if Path(tmp).stat().st_size<1024:raise RuntimeError('Backup too small')
 os.replace(tmp,final)
 def checksum(p):p.with_suffix(p.suffix+'.sha256').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
 checksum(final)
 # Keep one snapshot for each observed week, even if Sunday execution was missed.
 week=weekly/(now.strftime('%G-W%V')+'.dump.gpg')
 if not week.exists():shutil.copyfile(final,week);checksum(week)
 for folder,count in [(daily,7),(weekly,4)]:
  for old in sorted(folder.glob('*.dump.gpg'),reverse=True)[count:]:old.unlink();old.with_suffix(old.suffix+'.sha256').unlink(missing_ok=True)
 (base/'last-success.txt').write_text(now.isoformat()+' '+final.name+'\n')
 print('ConfigSentinel encrypted offsite backup complete: '+str(final))
finally:Path(tmp).unlink(missing_ok=True)
