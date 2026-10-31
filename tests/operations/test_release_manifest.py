import copy
from pathlib import Path
import runpy
import unittest

validate=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/check-release-manifest.py'))['validate']
class ImmutableReleaseGate(unittest.TestCase):
    def test_rejects_mutable_tags_unverified_scans_and_missing_approval(self):
        candidate={'commit':'a'*40,'homologation_passed':True,'production_approved':True}
        for name in ('api','web','db'):candidate[name]={'image':'ghcr.io/franklinlem/configsentinel-'+name+'@sha256:'+'b'*64,'sbom_sha256':'c'*64,'scan_high':0,'scan_critical':0,'provenance_verified':True}
        candidate['db']['image']='ghcr.io/franklinlem/configsentinel-db@sha256:'+'d'*64
        self.assertEqual(validate(candidate),[])
        self.assertTrue(validate([]))
        self.assertTrue(validate({'api':None}))
        for mutation in [lambda c:c['api'].update(image='ghcr.io/franklinlem/configsentinel-api:latest'),lambda c:c['web'].update(scan_high=1),lambda c:c.update(production_approved=False),lambda c:c['api'].update(provenance_verified=False)]:
            changed=copy.deepcopy(candidate);mutation(changed);self.assertTrue(validate(changed))
