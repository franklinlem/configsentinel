#!/usr/bin/env python3
"""Bounded smoke checks; prints statuses only, never response bodies or secrets."""
import argparse
import http.cookiejar
import json
import os
from pathlib import Path
import stat
import sys
import time
import urllib.error
import urllib.request

ORIGIN='https://configsentinel-dev.franklem.uk'

def credentials(path):
    st=path.lstat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=os.geteuid() or st.st_mode & 0o077:
        raise ValueError('unsafe credential file')
    data=json.loads(path.read_text())
    if set(data)!={'email','password'} or not all(isinstance(v,str) and v for v in data.values()):
        raise ValueError('invalid credentials')
    return data

def request(opener,path,body=None,csrf=''):
    headers={'Origin':ORIGIN,'Content-Type':'application/json','X-CSRF-Token':csrf}
    req=urllib.request.Request(ORIGIN+path,headers=headers,data=None if body is None else json.dumps(body).encode())
    try:
        with opener.open(req,timeout=15) as response:
            raw=response.read(1024*1024)
            data=json.loads(raw) if raw and 'application/json' in response.headers.get('Content-Type','') else {}
            return response.status,data
    except urllib.error.HTTPError as error:
        return error.code,{}

def run(auth,requester=request):
    opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    statuses={};failure=None
    try:
        # Bounded readiness retries account for routing propagation after deploy.
        for attempt in range(1,7):
            status,_=requester(opener,'/api/health/ready');statuses['readiness_attempt_'+str(attempt)]=status
            if status==200:break
            time.sleep(2)
        if status!=200:raise ValueError('readiness')
        statuses['site'],_=requester(opener,'/')
        statuses['events_unauthenticated'],_=requester(opener,'/api/v1/events')
        statuses['login'],login=requester(opener,'/api/v1/auth/login',auth)
        if statuses['login']!=200 or not isinstance(login.get('csrf_token'),str):raise ValueError('login')
        csrf=login['csrf_token']
        statuses['events'],_=requester(opener,'/api/v1/events')
        statuses['alerts'],_=requester(opener,'/api/v1/alerts')
        statuses['organizations'],_=requester(opener,'/api/v1/organizations')
        statuses['logout'],_=requester(opener,'/api/v1/auth/logout',{},csrf)
        statuses['after_logout'],_=requester(opener,'/api/v1/me')
        expected={'site':200,'events_unauthenticated':401,'login':200,'events':200,'alerts':200,'organizations':200,'logout':200,'after_logout':401}
        if any(statuses.get(k)!=v for k,v in expected.items()):raise ValueError('http_status')
    except Exception as exc:
        # Do not expose network exception text; it may contain sensitive URLs.
        failure=str(exc) if isinstance(exc,ValueError) and str(exc) in {'readiness','login','http_status'} else 'request_error'
    return {'status':'PASS' if failure is None else 'FAIL','failure':failure,'http_statuses':statuses,'secrets_recorded':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--credentials',required=True,type=Path);a=p.parse_args()
    try:auth=credentials(a.credentials)
    except Exception:
        print(json.dumps({'status':'FAIL','failure':'credentials_invalid'}));return 2
    result=run(auth);print(json.dumps(result,indent=2));return 0 if result['status']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
