"""Generate the versioned contract from explicit schemas (no source introspection)."""
import json
from pathlib import Path
S={}
def obj(props,required=()):return {'type':'object','additionalProperties':False,'properties':props,'required':list(required)}
def ref(name):return {'$ref':'#/components/schemas/'+name}
def st(**kw):return {'type':'string',**kw}
def uid():return st(format='uuid')
def dt():return st(format='date-time')
def integer(lo=0,hi=2147483647):return {'type':'integer','minimum':lo,'maximum':hi}
def nullable(v):return {'anyOf':[v,{'type':'null'}]}
def arr(v):return {'type':'array','items':v}
S['Problem']=obj({'type':st(),'title':st(),'status':integer(400,599),'detail':st()},['type','title','status','detail'])
S['Login']=obj({'email':st(format='email',maxLength=254),'password':st(minLength=1,maxLength=1024)},['email','password'])
S['LoginResult']=obj({'csrf_token':st(minLength=43,maxLength=43)},['csrf_token'])
S['OK']=obj({'ok':{'type':'boolean'}},['ok'])
S['ID']=obj({'id':uid()},['id'])
S['Me']=obj({'id':uid(),'email':st(format='email')},['id','email'])
S['NamedInput']=obj({'name':st(minLength=1,maxLength=120),'slug':st(pattern='^[a-z0-9][a-z0-9-]{0,62}$')},['name','slug'])
S['Organization']=obj({'id':uid(),'name':st(),'slug':st(),'created_at':dt(),'role':st(enum=['owner','admin','analyst','viewer']),'project_id':nullable(uid())},['id','name','slug','role'])
S['Project']=obj({'id':uid(),'organization_id':uid(),'name':st(),'slug':st()},['id','organization_id','name','slug'])
S['Environment']=obj({'id':uid(),'project_id':uid(),'name':st(),'slug':st()},['id','project_id','name','slug'])
S['ServerInput']=obj({'display_name':st(pattern='^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$')},['display_name'])
S['Server']=obj({'id':uid(),'display_name':st(),'environment_id':uid(),'environment':st(),'project':st(),'project_id':uid(),'organization_id':uid(),'agent_id':nullable(uid()),'last_seen_at':nullable(dt()),'last_observed_at':nullable(dt()),'agent_version':nullable(st()),'queue_depth':nullable(integer()),'clock_skew_warning':nullable({'type':'boolean'}),'status':st(enum=['online','offline','delayed','not_installed'])},['id','display_name','status'])
S['Credential']=obj({'agent_id':uid(),'token_id':uid(),'token':st(pattern='^cs_[A-Za-z0-9_-]{43}$')},['agent_id','token_id','token'])
S['Token']=obj({'id':uid(),'prefix':st(),'created_at':dt(),'expires_at':dt(),'revoked_at':nullable(dt())},['id','prefix','created_at','expires_at','revoked_at'])
hashv=st(pattern='^([a-f0-9]{64})?$')
kinds=['baseline','missing_initial','created','modified','deleted','unreadable','restored','recovered','metadata_changed','unstable']
S['AgentEvent']=obj({'event_uuid':uid(),'sequence':integer(1,9007199254740991),'file_alias':st(pattern='^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$'),'kind':st(enum=kinds),'old_sha256':hashv,'new_sha256':hashv,'file_size':integer(0,1073741824),'mode':integer(0,4095),'mtime':nullable(dt()),'observed_at':dt()},['event_uuid','sequence','file_alias','kind','observed_at'])
S['Batch']=obj({'batch_id':uid(),'schema_version':{'const':1},'events':{'type':'array','minItems':1,'maxItems':100,'items':ref('AgentEvent')}},['batch_id','schema_version','events'])
S['BatchResult']=obj({'accepted':arr(uid()),'duplicates':arr(uid()),'rejected':arr(uid())},['accepted','duplicates','rejected'])
S['Heartbeat']=obj({'agent_version':st(maxLength=40,enum=['0.1.0']),'queue_depth':integer(0,1000000),'observed_at':dt()},['agent_version','queue_depth','observed_at'])
S['HeartbeatResult']=obj({'ok':{'type':'boolean'},'server_time':dt(),'clock_skew_warning':{'type':'boolean'}},['ok','server_time','clock_skew_warning'])
S['AcknowledgementInput']=obj({'comment':st(minLength=3,maxLength=2000)},['comment'])
S['Acknowledgement']=obj({'id':uid(),'comment':st(),'actor':st(),'created_at':dt()},['id','comment','actor','created_at'])
props={**S['AgentEvent']['properties'],'id':uid(),'agent_id':uid(),'received_at':dt(),'payload_hash':st(),'severity':st(enum=['info','warning']),'server_name':st(),'server_id':uid(),'environment':st(),'acknowledged':{'type':'boolean'},'acknowledgements':arr(ref('Acknowledgement'))}
S['Event']=obj(props,['id','agent_id','event_uuid','sequence','file_alias','kind','observed_at','received_at'])
S['Observation']=obj({'agent_id':uid(),'file_alias':st(),'sha256':hashv,'state':st(enum=kinds),'file_size':integer(),'mode':integer(),'mtime':nullable(dt()),'observed_at':dt(),'received_at':dt(),'sequence':integer(1)},['agent_id','file_alias','sha256','state','observed_at','received_at','sequence'])
S['Alert']=obj({'id':uid(),'file_alias':st(),'kind':st(),'severity':st(),'received_at':nullable(dt()),'server_name':st(),'source':st(enum=['agent','event'])},['id','kind','severity','source'])
S['Audit']=obj({'id':uid(),'organization_id':uid(),'actor_id':nullable(uid()),'actor':nullable(st()),'operation':st(),'target_type':st(),'target_id':uid(),'data_redacted':obj({}),'timestamp':dt()},['id','organization_id','operation','target_type','target_id','timestamp'])
S['Member']=obj({'id':uid(),'email':st(format='email'),'role':st(enum=['owner','admin','analyst','viewer']),'project_id':nullable(uid())},['id','email','role','project_id'])
S['MemberInput']=obj({'email':st(format='email',maxLength=254),'password':st(minLength=16,maxLength=1024),'role':st(enum=['owner','admin','analyst','viewer']),'project_id':nullable(uid())},['email','password','role'])
for name in ['Organization','Project','Environment','Server','Token','Event','Observation','Alert','Audit','Member']:
 S[name+'List']=obj({'items':arr(ref(name)),**({'next_cursor':st()} if name=='Event' else {})},['items']+(['next_cursor'] if name=='Event' else []))
paths={}
def op(method,path,out,body=None,auth='admin',code=200,description=''):
 params=[]
 for part in path.split('/'):
  if part.startswith('{'):params.append({'name':part[1:-1],'in':'path','required':True,'schema':uid()})
 if auth=='admin' and method not in ['get']:params.extend([{'name':'X-CSRF-Token','in':'header','required':True,'schema':st()},{'name':'Origin','in':'header','required':True,'schema':st(format='uri')}])
 if path=='/auth/login':params.append({'name':'Origin','in':'header','required':True,'schema':st(format='uri')})
 errors={str(n):{'description':text,'content':{'application/problem+json':{'schema':ref('Problem')}}} for n,text in [(401,'Authentication required'),(403,'Scope, role, origin or CSRF denied'),(404,'Resource absent or outside scope'),(409,'Conflict / incompatible version / divergent replay'),(415,'Content type must be application/json'),(422,'Validation failed; no partial batch accepted'),(429,'Rate limited; Retry-After header'),(503,'Temporary database or service failure')]}
 operation={'operationId':method+'_'+path.replace('/','_').replace('{','').replace('}','').replace(':','_'),'description':description or ('Tenant and optional project scope derived from the session.' if auth=='admin' else 'Identity derived exclusively from agent bearer token.'),'security':([{'sessionCookie':[]}] if auth=='admin' else [{'agentBearer':[]}] if auth=='agent' else []),'parameters':params,'responses':{str(code):{'description':'Success','content':{'application/json':{'schema':ref(out)}}},**errors}}
 if body:operation['requestBody']={'required':True,'content':{'application/json':{'schema':ref(body)}}}
 paths.setdefault(path,{})[method]=operation
op('post','/auth/login','LoginResult','Login','public',description='Exact Origin required. Revocable 8-hour HttpOnly SameSite=Strict session cookie. CSRF token returned once to this browser session.')
op('post','/auth/logout','OK');op('get','/me','Me')
for base,name,parent in [('/organizations','Organization',None),('/organizations/{orgId}/projects','Project','owner'),('/projects/{projectId}/environments','Environment','manage')]:
 op('get',base,name+'List');op('post',base,'ID','NamedInput',code=201,description='Organization owner required.' if parent=='owner' or base=='/organizations' else 'Project admin or organization owner required.')
op('get','/environments/{envId}/servers','ServerList');op('post','/environments/{envId}/servers','ID','ServerInput',code=201)
op('get','/servers','ServerList');op('get','/servers/{serverId}','ServerList');op('get','/servers/{serverId}/observations','ObservationList')
op('post','/servers/{serverId}/agents','Credential',code=201,description='Admin/owner; one-time bearer token; new independent installation identity.')
op('get','/agents/{agentId}/tokens','TokenList');op('post','/agents/{agentId}/tokens','Credential',code=201,description='Admin/owner; issue new 90-day token without revoking existing tokens. Revoke old credential after host rotation.')
op('delete','/agents/{agentId}/tokens/{tokenId}','OK');op('get','/events','EventList');op('get','/events/{eventId}','EventList');op('post','/events/{eventId}/acknowledgements','ID','AcknowledgementInput',code=201,description='Analyst, project admin or owner. Recognition is not approval. Append-only acknowledgement audit.')
for name,schema in [('server_id',uid()),('environment_id',uid()),('kind',st(enum=kinds)),('q',st(maxLength=80)),('from',dt()),('to',dt()),('limit',integer(1,100)),('cursor',st())]:paths['/events']['get']['parameters'].append({'name':name,'in':'query','schema':schema,'description':'Opaque next_cursor from previous response' if name=='cursor' else 'Stable order by received_at DESC, id DESC' if name=='limit' else 'Filter'})
op('get','/alerts','AlertList');op('get','/organizations/{orgId}/audit-logs','AuditList',description='Owner only. Latest 100 administrative audit rows. Project admins do not receive organization-wide audit data.')
op('get','/organizations/{orgId}/members','MemberList');op('post','/organizations/{orgId}/members','ID','MemberInput',code=201,description='Owner only. Admin role requires a project in this organization. Existing user passwords are never overwritten.')
op('post','/agent/events:batch','BatchResult','Batch','agent',202,'Atomic batch, maximum 100 events / 1 MiB. UUID and sequence unique per agent. Identical replay returns duplicates; changed payload returns 409. Error means no ACK: retain local queue. No file content or paths accepted.')
op('post','/agent/heartbeat','HeartbeatResult','Heartbeat','agent',202)
S['Health']=obj({'status':st(),'version':st()},['status'])
for path in ['/api/health/live','/api/health/ready']:
 paths[path]={'get':{'operationId':path.rsplit('/',1)[1],'servers':[{'url':'/'}],'security':[],'responses':{'200':{'description':'Healthy','content':{'application/json':{'schema':ref('Health')}}},'503':{'description':'Not ready'}}}}
paths['/metrics']={'get':{'operationId':'metrics','servers':[{'url':'http://api:9090'}],'description':'Private Docker network only. Never routed through public nginx.','security':[],'responses':{'200':{'description':'Prometheus exposition','content':{'text/plain':{'schema':st()}}}}}}
doc={'openapi':'3.1.2','info':{'title':'ConfigSentinel API','version':'0.1.0','description':'Hash-only metadata observability. Bounded list endpoints; cursor pagination for events. Raw monitored file content and remote commands are never accepted.'},'servers':[{'url':'/api/v1'}],'paths':paths,'components':{'securitySchemes':{'sessionCookie':{'type':'apiKey','in':'cookie','name':'cs_session'},'agentBearer':{'type':'http','scheme':'bearer'}},'schemas':S}}
Path('api/openapi.yaml').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
