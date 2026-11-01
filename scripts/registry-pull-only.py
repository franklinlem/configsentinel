#!/usr/bin/env python3
"""Forced SSH command: pull only ConfigSentinel digest references, no deployment."""
import json
import os
import re
import subprocess
import sys
import tempfile


def main():
    stage = 'validate'
    try:
        request=json.loads(sys.stdin.buffer.read(65537))
        token=request['token'];images=request['images']
        if not isinstance(token,str) or not 20<=len(token)<=4096 or not isinstance(images,list) or not 1<=len(images)<=4:
            raise ValueError('invalid request')
        if any(not isinstance(ref,str) or not re.fullmatch(r'ghcr\.io/franklinlem/configsentinel-(api|web|db|agent)@sha256:[a-f0-9]{64}',ref) for ref in images):
            raise ValueError('invalid image')
        with tempfile.TemporaryDirectory(prefix='configsentinel-registry-') as folder:
            os.chmod(folder,0o700)
            env={**os.environ,'DOCKER_CONFIG':folder}
            stage = 'registry-login'
            subprocess.run(['docker','login','ghcr.io','--username','franklinlem','--password-stdin'],input=token.encode(),capture_output=True,env=env,check=True,timeout=30)
            for ref in images:
                stage = 'pull-' + ref.split('configsentinel-', 1)[1].split('@', 1)[0]
                subprocess.run(['docker','pull',ref],capture_output=True,env=env,check=True,timeout=180)
        print(json.dumps({'pulled':images,'deployed':False}))
        return 0
    except Exception as error:
        # Docker stderr may contain credential-bearing URLs. Emit categories only.
        reason = 'unexpected-failure'
        if isinstance(error, subprocess.TimeoutExpired):
            reason = 'timeout'
        elif isinstance(error, subprocess.CalledProcessError):
            detail = (error.stderr or b'').decode(errors='replace').lower()
            reason = 'docker-exit-' + str(error.returncode)
            for marker, category in [('unauthorized', 'registry-unauthorized'), ('denied', 'registry-denied'), ('no matching manifest', 'platform-mismatch'), ('manifest unknown', 'digest-not-found'), ('no space left', 'disk-full'), ('tls', 'tls-failure'), ('too many requests', 'registry-rate-limit'), ('unexpected status', 'registry-http-status'), ('connection', 'connection-failure')]:
                if marker in detail:
                    reason = category
                    break
        print('ConfigSentinel scoped registry pull failed: stage=' + stage + ' reason=' + reason,file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
