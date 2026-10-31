#!/usr/bin/env python3
"""Authenticated Laravel controller request via existing SSH, public API stays disabled."""
import subprocess,sys
from pathlib import Path
payload=sys.argv[1]
subprocess.run(['scp','-q','scripts/coolify-local-request.php','contabo:/tmp/configsentinel-request.php'],check=True)
subprocess.run(['scp','-q',payload,'contabo:/tmp/configsentinel-request.json'],check=True)
subprocess.run(['ssh','contabo','chmod 600 /tmp/configsentinel-request.json; docker cp /tmp/configsentinel-request.php coolify:/tmp/configsentinel-request.php; docker cp /tmp/configsentinel-request.json coolify:/tmp/configsentinel-request.json; docker exec -u root coolify php /tmp/configsentinel-request.php /tmp/configsentinel-request.json'],check=True)
