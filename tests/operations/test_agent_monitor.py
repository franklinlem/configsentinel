import io
import http.server
import threading
import urllib.request
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

m=runpy.run_path(str(Path(__file__).resolve().parents[2]/'scripts/monitor-agent-alerts.py'))
AGENT='11111111-1111-4111-8111-111111111111'

class AgentMonitor(unittest.TestCase):
    def test_only_scoped_alerts_and_fail_closed(self):
        def fetch(opener,path,body=None,csrf=''):
            if path=='/auth/login':return {'csrf_token':'synthetic'}
            if path=='/auth/logout':return {'ok':True}
            if path=='/servers':return {'items':[{'agent_id':AGENT}]}
            return {'items':alerts}
        config={'agent_ids':[AGENT],'email':'x','password':'fake'}
        with patch.dict(m['assess'].__globals__,{'request':fetch}):
            alerts=[{'id':AGENT,'source':'agent','kind':'queue_high'}]
            self.assertEqual(m['assess'](config,None)['status'],'down')
            alerts=[{'id':'other','source':'agent','kind':'agent_offline'}]
            self.assertEqual(m['assess'](config,None)['status'],'up')
            alerts=[{}]*100
            with self.assertRaises(ValueError):m['assess'](config,None)
    def test_delivery_to_isolated_http_sink(self):
        paths=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path); self.send_response(200); self.end_headers(); self.wfile.write(b'{"ok":true}')
            def log_message(self,*args): pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            config={'push_url':'http://127.0.0.1:'+str(server.server_port)+'/api/push/synthetic'}
            opener=urllib.request.build_opener()
            m['push'](config,{'status':'down','reason':'agent_alert'},opener)
            m['push'](config,{'status':'up','reason':'agents_healthy'},opener)
            self.assertIn('status=down',paths[0]); self.assertIn('status=up',paths[1])
            self.assertTrue(all(AGENT not in path for path in paths))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_private_config_and_sanitized_push(self):
        config={'email':'fake@example.invalid','password':'fake','agent_ids':[AGENT],'push_url':'http://127.0.0.1:3001/api/push/synthetic'}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json';p.write_text(json.dumps(config));p.chmod(0o600)
            self.assertEqual(m['load_config'](p),config)
            p.chmod(0o644)
            with self.assertRaises(ValueError):m['load_config'](p)
        class Reply(io.BytesIO):status=200
        class Opener:
            def open(self,url,timeout):
                self.url=url;return Reply(b'{"ok":true}')
        o=Opener();m['push'](config,{'status':'down','reason':'agent_alert'},o)
        self.assertIn('status=down',o.url);self.assertNotIn(AGENT,o.url)

if __name__=='__main__':unittest.main()
