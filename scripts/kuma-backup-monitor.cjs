// Run inside the existing Kuma container. All reads are local and secrets stay in memory.
const fs = require("fs");
const mysql = require("mysql2/promise");
const jwt = require("jsonwebtoken");
const { shake256, SHAKE256_LENGTH } = require("/app/server/util-server");
const { io } = require("socket.io-client");
(async () => {
  const config = JSON.parse(
    fs.readFileSync("/app/data/db-config.json", "utf8"),
  );
  let connection;
  if (config.type === "embedded-mariadb")
    connection = await mysql.createConnection({
      socketPath: "/app/data/run/mariadb.sock",
      user: require("os").userInfo().username,
      database: "kuma",
    });
  else if (config.type === "mariadb")
    connection = await mysql.createConnection({
      host: config.hostname,
      port: config.port,
      user: config.username,
      password: config.password,
      database: config.dbName,
      socketPath: config.socketPath,
    });
  else throw new Error("Unexpected Kuma storage; no changes made");
  const [users] = await connection.execute(
    "SELECT username,password FROM user WHERE active=1 ORDER BY id LIMIT 1",
  );
  const [settings] = await connection.execute(
    "SELECT value FROM setting WHERE `key`=?",
    ["jwtSecret"],
  );
  const user = users[0];
  const token = jwt.sign(
    { username: user.username, h: shake256(user.password, SHAKE256_LENGTH) },
    settings[0].value,
    { expiresIn: "5m" },
  );
  const name = "ConfigSentinel · Backup criptografado";
  const [existing] = await connection.execute("SELECT id,push_token FROM monitor WHERE name=? AND type='push'", [name]);
  await connection.end();
  if (existing.length) {
    process.stdout.write("http://127.0.0.1:3001/api/push/"+existing[0].push_token+"\n");
    return;
  }
  const socket = io("http://127.0.0.1:3001", {
    transports: ["websocket"],
    reconnection: false,
  });
  const timer = setTimeout(() => {
    socket.close();
    throw new Error("Kuma operation timeout");
  }, 20000);
  const emit = (event, ...args) =>
    new Promise((resolve, reject) =>
      socket.emit(event, ...args, (res) =>
        res?.ok
          ? resolve(res)
          : reject(new Error(res?.msg || "Kuma request failed")),
      ),
    );
  await new Promise((resolve, reject) => {
    socket.once("connect", resolve);
    socket.once("connect_error", reject);
  });
  await emit("loginByToken", token);
  const pushToken = require("crypto").randomBytes(24).toString("base64url");
  await emit("add", {
    type: "push", name, pushToken, accepted_statuscodes: ["200-200"],
    method: "GET", timeout: 15, maxredirects: 3, expiryNotification: false, ignoreTls: false,
    interval: 600, retryInterval: 60, resendInterval: 0,
    maxretries: 0, active: true, conditions: [],
    notificationIDList: { "1": true },
  });
  // stdout is redirected directly to a mode-0600 file, never a report.
  process.stdout.write("http://127.0.0.1:3001/api/push/"+pushToken+"\n");
  clearTimeout(timer);
  socket.close();
})().catch((e) => {
  console.error("Scoped ConfigSentinel backup monitor setup failed");
  process.exit(1);
});
