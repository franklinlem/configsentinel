#!/usr/bin/env python3
"""Strict, secret-safe J5 process protocol. Never logs child output or input."""
from __future__ import annotations
import json
import subprocess
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Diagnostic:
    category: str
    exit_code: int | None
    stdout_bytes: int
    stderr_bytes: int
    reason: str
    phase: str = 'protocol'
    kind: str = 'unknown'

class J5Failure(Exception):
    def __init__(self, diagnostic: Diagnostic):
        self.diagnostic = diagnostic
        super().__init__(f'{diagnostic.category}: {diagnostic.reason}')

def decode_response(exit_code: int, stdout: bytes, stderr: bytes) -> dict[str, Any]:
    def fail(category: str, reason: str, phase: str = 'protocol', kind: str = 'unknown') -> None:
        raise J5Failure(Diagnostic(category, exit_code, len(stdout), len(stderr), reason, phase, kind))
    if exit_code == 255:
        fail('transport', 'ssh_or_remote_exit_255')
    if len(stdout) > 65536 or len(stderr) > 65536:
        fail('parser', 'response_too_large')
    try:
        text = stdout.decode('utf-8', errors='strict')
        value = json.loads(text, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('invalid_constant')))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        if exit_code != 0:
            fail('helper', 'nonzero_exit_without_valid_envelope')
        fail('parser', 'invalid_json_or_encoding')
    if not isinstance(value, dict) or set(value) != {'version', 'status', 'data', 'error', 'phase', 'kind'} or value['version'] != 2:
        fail('parser', 'unexpected_envelope')
    if value['status'] == 'error':
        if (exit_code == 0 or value['data'] is not None or not isinstance(value['error'], str)
                or value['error'] not in {'invalid_input','scope_rejected','state_drift','transaction_failed','internal_error'}
                or not isinstance(value['phase'], str) or value['phase'] not in {'bootstrap','decode','apply','response'}
                or not isinstance(value['kind'], str) or value['kind'] not in {'output_buffer','php_warning','database','missing_model','invalid_json','runtime','other'}):
            fail('parser', 'invalid_error_envelope')
        fail('helper', value['error'], value['phase'], value['kind'])
    if exit_code != 0:
        fail('helper', 'nonzero_exit_with_success_envelope')
    if stderr:
        fail('helper', 'unexpected_stderr_after_success')
    if value['status'] != 'ok' or value['error'] is not None or value['phase'] != 'response' or value['kind'] is not None or not isinstance(value['data'], dict):
        fail('parser', 'invalid_success_envelope')
    data = value['data']
    if (set(data) != {'uuid', 'commit', 'changed', 'protected_envs_verified'}
            or not isinstance(data['uuid'], str) or data['uuid'] not in {'oi6lvzwzomwtbbgzf5uzofuh', 'configsentinel-j5-isolated'}
            or data['commit'] != '36baf66f4656f86d157cd070202323db9465c5f4'
            or type(data['changed']) is not bool or type(data['protected_envs_verified']) is not int or data['protected_envs_verified'] != 7):
        fail('parser', 'unexpected_success_data')
    return data

def invoke(command: list[str], payload: dict[str, Any], timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(command, input=json.dumps(payload, ensure_ascii=False).encode(), capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise J5Failure(Diagnostic('transport', None, len(exc.stdout or b''), len(exc.stderr or b''), 'timeout')) from None
    except OSError:
        raise J5Failure(Diagnostic('transport', None, 0, 0, 'spawn_failed')) from None
    return decode_response(result.returncode, result.stdout, result.stderr)
