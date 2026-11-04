import runpy
from pathlib import Path
import unittest
from unittest.mock import patch
m=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/smoke-homologation.py'))

class SmokeTest(unittest.TestCase):
    def test_readiness_retry_and_diagnostics(self):
        calls=[]
        def request(opener,path,body=None,csrf=''):
            calls.append(path)
            if path=='/api/health/ready':return (503 if calls.count(path)==1 else 200),{}
            if path=='/api/v1/auth/login':return 200,{'csrf_token':'synthetic'}
            if path in ['/api/v1/events','/api/v1/me'] and (calls.count('/api/v1/events')==1 or path.endswith('/me')):return 401,{}
            return 200,{}
        with patch.dict(m['run'].__globals__,{'time':type('Clock',(),{'sleep':staticmethod(lambda _:None)})}):
            result=m['run']({'email':'fake','password':'fake'},request)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['http_statuses']['readiness_attempt_1'],503)
    def test_failure_records_http_status_without_secrets(self):
        def request(opener,path,body=None,csrf=''):
            if path=='/api/health/ready':return 200,{}
            if path=='/api/v1/auth/login':return 401,{}
            return 200,{}
        result=m['run']({'email':'fake','password':'fake'},request)
        self.assertEqual(result['failure'],'login');self.assertEqual(result['http_statuses']['login'],401)
        self.assertNotIn('fake',str(result))
