#!/usr/bin/env python3
"""Validate a reviewed immutable candidate manifest; never publishes or deploys.

This validates declarations, not signatures or scan authenticity. Operators must
verify the referenced evidence separately before filling in approval fields.
"""
import argparse
import json
import re


def validate(manifest):
    if not isinstance(manifest, dict):
        return ['manifest must be an object']
    errors = []
    if not re.fullmatch('[0-9a-f]{40}', str(manifest.get('commit', ''))):
        errors.append('commit must be a full SHA')
    for name in ('api', 'web', 'db'):
        item = manifest.get(name, {})
        if not isinstance(item, dict):
            errors.append(name + ': image record must be an object')
            continue
        repository = 'ghcr.io/franklinlem/configsentinel-' + name
        if not re.fullmatch(re.escape(repository) + r'@sha256:[0-9a-f]{64}',
                            str(item.get('image', ''))):
            errors.append(name + ': exact approved repository digest required')
        if not re.fullmatch('[0-9a-f]{64}', str(item.get('sbom_sha256', ''))):
            errors.append(name + ': SBOM checksum required')
        if item.get('scan_high') != 0 or item.get('scan_critical') != 0:
            errors.append(name + ': HIGH/CRITICAL gate not passed')
        if item.get('provenance_verified') is not True:
            errors.append(name + ': provenance not verified')
    if manifest.get('homologation_passed') is not True:
        errors.append('same digests must pass homologation')
    if manifest.get('production_approved') is not True:
        errors.append('explicit production approval required')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    args = parser.parse_args()
    try:
        with open(args.manifest) as stream:
            errors = validate(json.load(stream))
    except (OSError, ValueError, TypeError):
        errors = ['invalid or unavailable manifest']
    print(json.dumps({'status': 'NO-GO' if errors else 'candidate-gates-passed',
                      'errors': errors}))
    return 2 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
