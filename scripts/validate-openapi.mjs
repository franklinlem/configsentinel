import fs from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(
  new URL("../apps/web/package.json", import.meta.url),
);
const parser = require("@apidevtools/swagger-parser");
const source = JSON.parse(
  fs.readFileSync(new URL("../api/openapi.yaml", import.meta.url), "utf8"),
);
await parser.validate(source);
console.log(
  `OpenAPI ${source.openapi}: ${Object.keys(source.paths).length} paths validated`,
);
