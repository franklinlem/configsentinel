#!/usr/bin/env python3
"""Prepare SSH invocation with fixed program and structured stdin; never print secrets."""
from pathlib import Path
import shlex
from j5_protocol import invoke

def remote_command() -> list[str]:
    base=Path(__file__).resolve().parent
    # Fixed source, no interpolation of inputs into PHP or shell; JSON travels on stdin.
    source='?>\n'+(base/'j5_coolify_transaction.php').read_text()+'\n?>\n'+(base/'j5_coolify_entry.php').read_text()
    return ['ssh','-o','BatchMode=yes','contabo','docker exec -i coolify php -r '+shlex.quote(source)]

def configure(payload: dict) -> dict:
    return invoke(remote_command(),payload,timeout=60)
