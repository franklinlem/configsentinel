#!/usr/bin/env python3
"""Reverify signed candidate and fallback with a read-only registry token; no deploy."""
import argparse
import base64
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def statements(path):
    remaining = path.read_text().strip()
    decoder = json.JSONDecoder()
    while remaining:
        value, end = decoder.raw_decode(remaining)
        for envelope in value if isinstance(value, list) else [value]:
            yield json.loads(base64.b64decode(envelope['payload']))
        remaining = remaining[end:].strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.local/readonly-pull'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    candidate = json.loads(Path('deploy/release-manifest.candidate.json').read_text())
    fallback = json.loads(Path('deploy/release-manifest.fallback.json').read_text())
    results = []
    for label, record, sbom_path in [
        *[(f'candidate-{c}', candidate[c], Path(f'docs/evidence/remediation/{c}-sbom.cdx.json')) for c in ('api', 'web', 'db', 'agent')],
        ('fallback-api', fallback['api'], Path('docs/evidence/promotion/fallback-api-sbom.cdx.json')),
    ]:
        component = record['component']
        reference = record['image']
        repository = f'ghcr.io/franklinlem/configsentinel-{component}'
        if not re.fullmatch(re.escape(repository)+r'@sha256:[a-f0-9]{64}', reference):
            raise ValueError('Unapproved image repository or digest')
        if hashlib.sha256(sbom_path.read_bytes()).hexdigest() != record['sbom_sha256']:
            raise ValueError('SBOM checksum mismatch')
        folder = args.output/label
        folder.mkdir(exist_ok=True)
        common = [os.environ['COSIGN_BIN'], '--key', 'deploy/release-signing.pub', '--insecure-ignore-tlog']
        commands = [('signature', [common[0], 'verify', *common[1:], reference])]
        for kind, attestation_type in [('provenance', 'slsaprovenance1'), ('sbom', 'cyclonedx')]:
            commands.append((kind, [common[0], 'verify-attestation', *common[1:], '--type', attestation_type, reference]))
        for kind, command in commands:
            with (folder/(kind+'.json')).open('w') as stream, (folder/(kind+'.log')).open('w') as log:
                subprocess.run(command, stdout=stream, stderr=log, check=True, timeout=120)
        digest = reference.split('@sha256:')[1]
        for kind in ('provenance', 'sbom'):
            decoded = list(statements(folder/(kind+'.json')))
            bound = [s for s in decoded if any(v['name'] == repository and v['digest'].get('sha256') == digest for v in s['subject'])]
            if not bound:
                raise ValueError('Signed subject mismatch')
            if kind == 'provenance':
                expected = {'repository': 'https://github.com/franklinlem/configsentinel', 'commit': record['commit'], 'component': component, 'platform': 'linux/amd64'}
                if not any(all(s['predicate']['buildDefinition']['externalParameters'].get(k) == v for k, v in expected.items()) for s in bound):
                    raise ValueError('Signed provenance mismatch')
            elif not any(s['predicate'] == json.loads(sbom_path.read_text()) for s in bound):
                raise ValueError('Signed SBOM mismatch')
        with (folder/'scan.log').open('w') as log:
            subprocess.run([os.environ['TRIVY_BIN'], 'image', '--scanners', 'vuln', '--format', 'json', '--output', str(folder/'scan.json'), reference], stdout=log, stderr=log, check=True, timeout=240)
        scan = json.loads((folder/'scan.json').read_text())
        counts = collections.Counter(v['Severity'] for r in scan.get('Results', []) for v in r.get('Vulnerabilities', []))
        if counts['HIGH'] or counts['CRITICAL']:
            raise ValueError('Blocking vulnerabilities detected')
        results.append({'label': label, 'image': reference, 'commit': record['commit'], 'signature_verified': True, 'provenance_verified': True, 'signed_sbom_matches': True, 'scan_counts': dict(counts)})
    (args.output/'results.json').write_text(json.dumps({'images': results, 'registry_access': 'read-only job token', 'deployed': False}, indent=2)+'\n')
    print('Five immutable images verified with pinned key and current vulnerability database; no deploy')


if __name__ == '__main__':
    main()
