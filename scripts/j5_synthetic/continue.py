#!/usr/bin/env python3
"""Continue only existing synthetic resources after a harness-only correction.
No container creation, deletion, restart, active database reads or automatic retry.
"""
import json
from pathlib import Path
import re
import time
import run as harness

if __name__ == '__main__':
    context = json.loads((Path(__file__).parent / 'resume-state.json').read_text())
    harness.REPORT.update(context)
    harness.REPORT.pop('failure', None)
    harness.REPORT['result'] = 'FAIL'
    harness.REPORT['steps'] = []
    harness.REPORT['started_at_unix'] = time.time()
    try:
        resource = context['resources']
        if not re.fullmatch(r'configsentinel-j5-phase1-[a-f0-9]{10}', resource['name']):
            raise RuntimeError('invalid_resource_prefix')
        if any(not re.fullmatch(r'[a-f0-9]{64}', resource[k]) for k in ('network_id','db_container_id','php_container_id')):
            raise RuntimeError('invalid_resource_ids')
        net = harness.inspect_resource('network', resource['network_id'])
        expected = {resource['db_container_id'], resource['php_container_id']}
        label = {'configsentinel.j5.phase1': resource['name']}
        if (not net['Internal'] or set(net['Containers']) != expected or net['Labels'] != label
                or net['Options'].get('com.docker.network.bridge.gateway_mode_ipv4') != 'isolated'):
            raise RuntimeError('network_scope_drift')
        for cid, image in ((resource['db_container_id'], harness.POSTGRES), (resource['php_container_id'], harness.COOLIFY)):
            info = json.loads(harness.docker('inspect', cid, phase='resume_scope').stdout)[0]
            config = info['HostConfig']
            if (info['Image'] != image or info['Config']['Labels'].get('configsentinel.j5.phase1') != resource['name']
                    or config.get('PortBindings') or config['Privileged'] or config['CapAdd']
                    or config['CapDrop'] != ['ALL'] or not config['ReadonlyRootfs']
                    or any(m['Type'] != 'tmpfs' for m in info['Mounts'])
                    or set(info['NetworkSettings']['Networks']) != {resource['name']+'-net'}
                    or config['Memory'] not in (256*1024**2, 512*1024**2)
                    or not info['State']['Running']):
                raise RuntimeError('container_scope_drift')
        harness.exercise(resource['db_container_id'], resource['php_container_id'])
    except Exception as error:
        harness.REPORT['failure'] = {'category': type(error).__name__, 'phase': harness.REPORT['steps'][-1]['phase'] if harness.REPORT['steps'] else 'resume_scope', 'code': str(error) if type(error) is RuntimeError else 'unexpected_exception'}
    harness.REPORT['duration_seconds'] = round(time.time()-harness.REPORT['started_at_unix'], 3)
    print(json.dumps(harness.REPORT, indent=2))
    raise SystemExit(0 if harness.REPORT['result']=='PASS' else 2)
