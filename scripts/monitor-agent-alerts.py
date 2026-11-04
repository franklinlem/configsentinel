#!/usr/bin/env python3
"""Push scoped agent health to a dedicated Uptime Kuma monitor.

Credentials and the push URL stay in a 0600 local JSON file; only status codes
and fixed categories are emitted. A full or incomplete alert listing fails
closed instead of claiming healthy. No monitored file paths are read.
"""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import stat
import urllib.parse
import urllib.request
import uuid

AGENT_KINDS = frozenset(('agent_offline', 'collection_delayed', 'queue_high', 'clock_skew'))
ORIGIN = 'https://configsentinel-dev.franklem.uk'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_config(path):
    path = Path(path)
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
        raise ValueError('unsafe configuration')
    config = json.loads(path.read_text())
    if set(config) != {'email', 'password', 'agent_ids', 'push_url'}:
        raise ValueError('invalid configuration')
    if not isinstance(config['email'], str) or not config['email'] or not isinstance(config['password'], str) or not config['password']:
        raise ValueError('invalid credentials')
    ids = config['agent_ids']
    if not isinstance(ids, list) or not ids or len(ids) > 100 or len(ids) != len(set(ids)):
        raise ValueError('invalid agents')
    for value in ids:
        if not isinstance(value, str) or str(uuid.UUID(value)) != value:
            raise ValueError('invalid agent id')
    parsed = urllib.parse.urlsplit(config['push_url'])
    if (parsed.scheme, parsed.netloc) not in {('http','127.0.0.1:3001'), ('https','status.franklem.uk')} or not parsed.path.startswith('/api/push/') or parsed.query or parsed.fragment:
        raise ValueError('invalid destination')
    return config


def request(opener, path, body=None, csrf=''):
    headers = {'Origin': ORIGIN, 'Content-Type': 'application/json', 'X-CSRF-Token': csrf}
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(ORIGIN+'/api/v1'+path, data=data, headers=headers)
    with opener.open(req, timeout=15) as response:
        if response.status != 200:
            raise ValueError('unexpected response')
        return json.loads(response.read(1024*1024))


def assess(config, opener):
    session = request(opener, '/auth/login', {'email':config['email'], 'password':config['password']})
    csrf = session['csrf_token']
    try:
        alerts = request(opener, '/alerts')['items']
        servers = request(opener, '/servers')['items']
        if not isinstance(alerts,list) or not isinstance(servers,list) or len(alerts)>=100 or len(servers)>=100:
            raise ValueError('incomplete listing')
        selected = set(config['agent_ids'])
        if not selected.issubset({s.get('agent_id') for s in servers}):
            raise ValueError('agent not visible')
        found = {a.get('kind') for a in alerts if a.get('source') == 'agent' and a.get('id') in selected and a.get('kind') in AGENT_KINDS}
        return {'status':'down' if found else 'up','reason':'agent_alert' if found else 'agents_healthy'}
    finally:
        try: request(opener, '/auth/logout', {}, csrf)
        except Exception: pass


def push(config, report, opener):
    query=urllib.parse.urlencode({'status':report['status'], 'msg':report['reason']})
    with opener.open(config['push_url']+'?'+query, timeout=15) as response:
        if response.status != 200 or json.loads(response.read(65536)).get('ok') is not True:
            raise ValueError('delivery failed')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    args=parser.parse_args()
    try:
        config=load_config(args.config)
    except Exception:
        print(json.dumps({'status':'error','reason':'configuration_invalid'}));return 2
    opener=urllib.request.build_opener(NoRedirect(), urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    try: report=assess(config,opener)
    except Exception: report={'status':'down','reason':'agent_check_failed'}
    try: push(config,report,opener)
    except Exception:
        print(json.dumps({'status':'error','reason':'monitor_delivery_failed'}));return 2
    print(json.dumps(report));return 0 if report['status']=='up' else 1

if __name__ == '__main__':
    raise SystemExit(main())
