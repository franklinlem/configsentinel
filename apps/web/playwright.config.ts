import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "../../tests/e2e",
  workers: 1,
  use: {
    baseURL: process.env.E2E_URL || "http://localhost:8080",
    headless: true,
    trace: "retain-on-failure",
  },
  reporter: "list",
});
