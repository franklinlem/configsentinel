// Run inside Kuma. stdout contains a secret and must be captured privately.
const mysql = require('mysql2/promise');
const jwt = require('jsonwebtoken');
const {shake256, SHAKE256_LENGTH} = require('/app/server/util-server');
const {io} = require('socket.io-client');
const crypto = require('crypto');
(async () => {
  const db = await mysql.createConnection({socketPath:'/app/data/run/mariadb.sock', user:require('os').userInfo().username, database:'kuma'});
  const name='ConfigSentinel · Agente sintético';
  const [existing]=await db.execute('SELECT id,push_token,active FROM monitor WHERE name=? AND type=?',[name,'push']);
  const [channels]=await db.execute('SELECT n.id FROM notification n JOIN monitor_notification mn ON mn.notification_id=n.id WHERE mn.monitor_id=? AND n.name=?',[21,'HermesFranklem']);
  if(channels.length!==1 || existing.length>1) throw Error('monitor_scope');
  if(existing.length===1) {
    const [linked]=await db.execute('SELECT notification_id FROM monitor_notification WHERE monitor_id=?',[existing[0].id]);
    if(!existing[0].active || linked.length!==1 || linked[0].notification_id!==channels[0].id) throw Error('monitor_drift');
    process.stdout.write(JSON.stringify({id:existing[0].id,token:existing[0].push_token,created:false}));
    await db.end(); return;
  }
  const [users]=await db.execute('SELECT username,password FROM user WHERE active=1 ORDER BY id LIMIT 1');
  const [settings]=await db.execute('SELECT value FROM setting WHERE `key`=?',['jwtSecret']);
  if(users.length!==1 || settings.length!==1) throw Error('authentication_unavailable');
  const token=jwt.sign({username:users[0].username,h:shake256(users[0].password,SHAKE256_LENGTH)},settings[0].value,{expiresIn:'5m'});
  await db.end();
  const socket=io('http://127.0.0.1:3001',{transports:['websocket'],reconnection:false});
  const timer=setTimeout(()=>{socket.close();process.exit(2)},20000);
  const emit=(event,...args)=>new Promise((resolve,reject)=>socket.emit(event,...args,r=>r?.ok?resolve(r):reject(Error('kuma_request_failed'))));
  await new Promise((resolve,reject)=>{socket.once('connect',resolve);socket.once('connect_error',reject)});
  await emit('loginByToken',token);
  const pushToken=crypto.randomBytes(24).toString('base64url');
  const result=await emit('add',{type:'push',name,pushToken,accepted_statuscodes:['200-200'],method:'GET',timeout:15,maxredirects:3,expiryNotification:false,ignoreTls:false,interval:600,retryInterval:60,resendInterval:0,maxretries:0,active:true,conditions:[],notificationIDList:{[channels[0].id]:true}});
  process.stdout.write(JSON.stringify({id:result.monitorID,token:pushToken,created:true}));
  clearTimeout(timer);socket.close();
})().catch(()=>{process.stderr.write('Scoped agent monitor setup failed\n');process.exitCode=2});
