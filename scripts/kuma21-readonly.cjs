// Run only inside Kuma. No notifier config, push token, JWT or password is read.
(async () => {
  const mysql = require('mysql2/promise');
  const connection = await mysql.createConnection({
    socketPath: '/app/data/run/mariadb.sock',
    user: require('os').userInfo().username,
    database: 'kuma',
  });
  try {
    await connection.query('START TRANSACTION READ ONLY');
    const [monitor] = await connection.execute('SELECT id,name,type,active,`interval`,retry_interval,maxretries FROM monitor WHERE id=21');
    const [history] = await connection.execute('SELECT status,msg,time FROM heartbeat WHERE monitor_id=21 ORDER BY id DESC LIMIT 5');
    const [notification_names] = await connection.execute('SELECT n.id,n.name FROM notification n JOIN monitor_notification mn ON mn.notification_id=n.id WHERE mn.monitor_id=21');
    console.log(JSON.stringify({ checked_at: new Date().toISOString(), monitor, history, notification_names, scope: 'read-only metadata/history of ConfigSentinel monitor 21; no credentials/global settings accessed' }, null, 2));
  } finally {
    await connection.rollback();
    await connection.end();
  }
})().catch(() => { console.error('ConfigSentinel monitor metadata query failed'); process.exitCode = 2; });
