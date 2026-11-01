import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('j5_protocol', pathlib.Path(__file__).resolve().parents[2]/'scripts/j5_protocol.py')
m = importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)

class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.ok=json.dumps({'version':1,'status':'ok','data':{'uuid':'configsentinel-j5-isolated','commit':'36baf66f4656f86d157cd070202323db9465c5f4','changed':True,'protected_envs_verified':7},'error':None}).encode()
    def test_valid(self):self.assertEqual(m.decode_response(0,self.ok,b'')['commit'],'36baf66f4656f86d157cd070202323db9465c5f4')
    def test_invalid_outputs(self):
        for output in [b'',self.ok[:-1],b'prefix '+self.ok,self.ok+b' extra',b'\xff',b'null',b'{"version": NaN}',b'{}']:
            with self.subTest(output=output):
                with self.assertRaises(m.J5Failure) as e:m.decode_response(0,output,b'')
                self.assertEqual(e.exception.diagnostic.category,'parser')
    def test_transport_and_helper(self):
        error=json.dumps({'version':1,'status':'error','data':None,'error':'transaction_failed'}).encode()
        for code,out,category in [(255,b'password=secret','transport'),(2,error,'helper'),(1,b'raw secret','helper'),(1,self.ok,'helper')]:
            with self.subTest(code=code,out=out):
                with self.assertRaises(m.J5Failure) as e:m.decode_response(code,out,b'token=secret')
                self.assertEqual(e.exception.diagnostic.category,category);self.assertNotIn('secret',str(e.exception))
    def test_boundary_and_timeout(self):
        with self.assertRaises(m.J5Failure) as e:m.decode_response(0,b'x'*65537,b'')
        self.assertEqual(e.exception.diagnostic.reason,'response_too_large')
        with self.assertRaises(m.J5Failure) as e:m.invoke([sys.executable,'-c','import time;time.sleep(2)'],{},timeout=0.1)
        self.assertEqual(e.exception.diagnostic.category,'transport')
    def test_diagnostics_never_echo_response(self):
        with self.assertRaises(m.J5Failure) as e:m.decode_response(0,b'private-token',b'password')
        self.assertEqual(e.exception.diagnostic.stdout_bytes,13);self.assertEqual(e.exception.diagnostic.stderr_bytes,8)
        self.assertNotIn('private',repr(e.exception.diagnostic));self.assertNotIn('password',repr(e.exception.diagnostic))
    def test_unexpected_success_data_is_not_returned(self):
        data=json.loads(self.ok);data['data']['secret']='private-token'
        with self.assertRaises(m.J5Failure) as e:m.decode_response(0,json.dumps(data).encode(),b'')
        self.assertEqual(e.exception.diagnostic.reason,'unexpected_success_data')
    def test_secret_payload_is_only_sent_on_stdin(self):
        response=subprocess.CompletedProcess(['fixed-command'],0,self.ok,b'')
        with patch.object(m.subprocess,'run',return_value=response) as call:
            m.invoke(['fixed-command'],{'password':'private-synthetic'})
        args,kw=call.call_args
        self.assertNotIn('private-synthetic',repr(args))
        self.assertIn(b'private-synthetic',kw['input'])
    def test_success_with_stderr_is_not_accepted(self):
        with self.assertRaises(m.J5Failure) as e:m.decode_response(0,self.ok,b'possibly sensitive warning')
        self.assertEqual(e.exception.diagnostic.reason,'unexpected_stderr_after_success')
        self.assertNotIn('sensitive',str(e.exception))
if __name__=='__main__':unittest.main()
