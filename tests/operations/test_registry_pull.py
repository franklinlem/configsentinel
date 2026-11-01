"""Verify the restricted pull helper never logs credential-bearing Docker errors."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('configsentinel_scoped_pull', Path(__file__).resolve().parents[2]/'scripts/registry-pull-only.py')
pull = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pull)


class RestrictedRegistryPull(unittest.TestCase):
    reference = 'ghcr.io/franklinlem/configsentinel-api@sha256:'+'a'*64
    sentinel = 'DO_NOT_EMIT_FAKE_CREDENTIAL_123456789'

    def invoke(self, images, docker_effect):
        request = json.dumps({'token': self.sentinel, 'images': images}).encode()
        output, errors = io.StringIO(), io.StringIO()
        with patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(request))), patch.object(pull.subprocess, 'run', side_effect=docker_effect) as docker, contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = pull.main()
        combined = output.getvalue()+errors.getvalue()
        self.assertNotIn(self.sentinel, combined)
        return code, combined, docker

    def test_rejects_out_of_scope_repository_before_docker(self):
        code, _, docker = self.invoke(['ghcr.io/unrelated/project@sha256:'+'a'*64], [])
        self.assertEqual(code, 2)
        docker.assert_not_called()

    def test_login_error_redacts_credential_url(self):
        error = subprocess.CalledProcessError(1, ['docker'], stderr=('unauthorized https://'+self.sentinel+'@registry.invalid').encode())
        code, report, _ = self.invoke([self.reference], [error])
        self.assertEqual(code, 2)
        self.assertIn('stage=registry-login', report)
        self.assertIn('registry-unauthorized', report)

    def test_pull_error_reports_only_component_and_category(self):
        error = subprocess.CalledProcessError(1, ['docker'], stderr=('unexpected status https://registry.invalid?token='+self.sentinel).encode())
        code, report, _ = self.invoke([self.reference], [subprocess.CompletedProcess([], 0), error])
        self.assertEqual(code, 2)
        self.assertIn('stage=pull-api', report)
        self.assertIn('registry-http-status', report)
        self.assertNotIn('registry.invalid', report)

    def test_success_uses_removed_private_docker_config(self):
        code, report, docker = self.invoke([self.reference], [subprocess.CompletedProcess([], 0), subprocess.CompletedProcess([], 0)])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(report)['deployed'])
        configs = [call.kwargs['env']['DOCKER_CONFIG'] for call in docker.call_args_list]
        self.assertEqual(len(set(configs)), 1)
        self.assertFalse(Path(configs[0]).exists())
        self.assertNotEqual(Path(configs[0]), Path.home()/'.docker')


if __name__ == '__main__':
    unittest.main()
