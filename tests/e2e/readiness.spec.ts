import { test, expect } from "../../apps/web/node_modules/@playwright/test";
import AxeBuilder from "../../apps/web/node_modules/@axe-core/playwright";
import fs from "node:fs";
const vars = Object.fromEntries(
  fs
    .readFileSync(process.env.E2E_ENV_FILE || ".local/dev.env", "utf8")
    .trim()
    .split("\n")
    .map((line) => {
      const i = line.indexOf("=");
      return [line.slice(0, i), line.slice(i + 1)];
    }),
);
async function login(
  page: import("../../apps/web/node_modules/@playwright/test").Page,
) {
  await page.goto("/");
  await page.getByLabel("E-mail", { exact: true }).fill(vars.ADMIN_EMAIL);
  await page.getByLabel("Senha", { exact: true }).fill(vars.ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Entrar no ConfigSentinel" }).click();
  await expect(
    page.getByRole("heading", { name: "Visão geral", exact: true }),
  ).toBeVisible();
}
test("all pages: axe, responsive navigation, dialog and API errors", async ({
  page,
}) => {
  await login(page);
  const findings: unknown[] = [];
  for (const name of [
    "Visão geral",
    "Eventos",
    "Servidores",
    "Projetos e ambientes",
    "Credenciais",
    "Membros",
    "Auditoria",
  ]) {
    await page
      .getByRole("navigation")
      .getByRole("link", { name, exact: true })
      .click();
    await page.waitForTimeout(150);
    const result = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    findings.push(
      ...result.violations.map((v) => ({
        page: name,
        id: v.id,
        nodes: v.nodes.map((n) => n.target),
      })),
    );
  }
  console.log("READINESS_A11Y_FINDINGS", JSON.stringify(findings));
  expect(findings).toEqual([]);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Eventos", exact: true })
    .click();
  await page.route("**/api/v1/events?**", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/problem+json",
      body: JSON.stringify({
        detail: "Falha sintética de rede: revisão de prontidão",
      }),
    }),
  );
  await page.getByLabel("Buscar alias").fill("synthetic-review-failure");
  await expect(page.getByRole("alert")).toContainText("Falha sintética");
  await page.unroute("**/api/v1/events?**");
  for (const width of [390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
});
test("one-time credential stays out of browser storage and vanishes after closing", async ({
  page,
}) => {
  await login(page);
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Credenciais", exact: true })
    .click();
  const synthetic = "cs_" + "z".repeat(43);
  await page.route("**/api/v1/servers/*/agents", (route) =>
    route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        agent_id: "00000000-0000-4000-8000-000000000001",
        token_id: "00000000-0000-4000-8000-000000000002",
        token: synthetic,
      }),
    }),
  );
  await page
    .getByRole("button", { name: "Provisionar nova instalação" })
    .click();
  await expect(page.getByLabel("Token", { exact: true })).toHaveValue(
    synthetic,
  );
  const persisted = await page.evaluate(() =>
    JSON.stringify({
      local: { ...localStorage },
      session: { ...sessionStorage },
    }),
  );
  expect(persisted).not.toContain(synthetic);
  await page.getByRole("button", { name: "Credencial guardada" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByLabel("Token", { exact: true })).toHaveCount(0);
});
test("initial API outage characterization", async ({ page }) => {
  await page.route("**/api/v1/me", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/problem+json",
      body: JSON.stringify({ detail: "synthetic service unavailable" }),
    }),
  );
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Acesse seu observatório" }),
  ).toBeVisible();
  console.log(
    "READINESS_KNOWN_GAP: initial /me 503 is presented as login without an availability error",
  );
});
