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
  const name = "ConfigSentinel · Homologação";
  const url = "https://configsentinel-dev.franklem.uk/api/health/ready";
  const [existing] = await connection.execute(
    "SELECT id,name,url,active,`interval` FROM monitor WHERE name=? OR url=?",
    [name, url],
  );
  await connection.end();
  if (existing.length) {
    console.log(JSON.stringify({ existing }));
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
  const result = await emit("add", {
    type: "http",
    name,
    url,
    method: "GET",
    interval: 60,
    retryInterval: 30,
    resendInterval: 0,
    maxretries: 2,
    timeout: 15,
    expiryNotification: false,
    ignoreTls: false,
    maxredirects: 3,
    accepted_statuscodes: ["200-200"],
    notificationIDList: {},
    active: true,
    conditions: [],
  });
  console.log(
    JSON.stringify({ monitorID: result.monitorID, name, url, interval: 60 }),
  );
  clearTimeout(timer);
  socket.close();
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
