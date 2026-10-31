// Signs in to a web app on the project's own Playwright and writes a storageState file.
//
// Called only by `devteam qa auth` (qa_auth.py). One JSON document on stdin, never argv:
//   { mode: "recipe" | "interactive", project_root, out_path, timeout_ms,
//     recipe: { url, username_selector, password_selector, submit_selector,
//               totp_selector?, success_url_contains? },
//     username?, password?, totp? }
// One JSON line on stdout: { ok: true } or { ok: false, reason, message }.
// Secrets are used and dropped; nothing here prints, logs or echoes one, and error text is
// fixed rather than taken from Playwright, whose messages can quote what was typed.

import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

function reply(body, code = 0) {
  process.stdout.write(JSON.stringify(body) + "\n", () => process.exit(code));
}

const fail = (reason, message, code = 3) => reply({ ok: false, reason, message }, code);

async function readStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(chunk);
  return Buffer.concat(chunks).toString("utf8");
}

function loadPlaywright(root) {
  const require = createRequire(path.join(root, "package.json"));
  for (const name of ["playwright", "@playwright/test", "playwright-core"]) {
    try {
      const mod = require(name);
      if (mod && mod.chromium) return mod;
    } catch {
      // not installed under that name
    }
  }
  return null;
}

// The browser this script opened, so a SIGTERM (the CLI's timeout, a Ctrl-C) closes it.
let openBrowser = null;
const SIGNALS = { SIGHUP: 1, SIGINT: 2, SIGTERM: 15 };
for (const [signal, number] of Object.entries(SIGNALS)) {
  process.on(signal, async () => {
    try {
      if (openBrowser) await openBrowser.close();
    } catch {
      // already gone
    }
    process.exit(128 + number);
  });
}

// The same rules the CLI applied to login.url (qa_auth.check_login_url), applied to the page the
// browser actually landed on: a redirect must not carry the credentials somewhere else.
const DEFAULT_PORTS = { "http:": "80", "https:": "443" };

function urlAllowed(raw, rules) {
  let u;
  try {
    u = new URL(raw);
  } catch {
    return false;
  }
  if (u.username || u.password || !u.hostname) return false;
  const host = u.hostname.replace(/^\[|\]$/g, "").toLowerCase();
  if (u.protocol === "http:") {
    const loopback = host === "localhost" || host === "127.0.0.1" || host === "::1" || host.endsWith(".localhost");
    if (!loopback || rules.production) return false;
  } else if (u.protocol !== "https:") {
    return false;
  }
  if (rules.host) {
    if (host !== rules.host) return false;
    if (rules.port && (u.port || DEFAULT_PORTS[u.protocol]) !== String(rules.port)) return false;
  }
  return true;
}

const BAD_URL = { reason: "invalid-login-url", message: "the login page is not at an address the credentials group allows" };

function save(state, outPath) {
  fs.writeFileSync(outPath, JSON.stringify(state), { mode: 0o600 });
  fs.chmodSync(outPath, 0o600);
}

async function recipeLogin(browser, input) {
  const r = input.recipe || {};
  const timeout = input.timeout_ms || 30000;
  const context = await browser.newContext();
  const page = await context.newPage();
  page.setDefaultTimeout(timeout);
  let step = "open the login page";
  try {
    await page.goto(r.url, { waitUntil: "load" });
    if (!urlAllowed(page.url(), input.url_rules || {})) {
      await browser.close().catch(() => {});
      return BAD_URL;
    }
    step = "fill the username";
    await page.fill(r.username_selector, input.username);
    step = "fill the password";
    await page.fill(r.password_selector, input.password);
    step = "submit the form";
    await page.click(r.submit_selector);
    if (input.totp && r.totp_selector) {
      step = "enter the one-time code";
      await page.waitForSelector(r.totp_selector, { state: "visible" });
      await page.fill(r.totp_selector, input.totp);
      await page.press(r.totp_selector, "Enter");
    }
    step = "reach the signed-in page";
    if (r.success_url_contains) {
      await page.waitForURL((url) => url.toString().includes(r.success_url_contains));
    } else {
      await page.waitForLoadState("networkidle");
    }
  } catch {
    return { reason: "login-failed", message: `sign-in failed: could not ${step}` };
  }
  save(await context.storageState(), input.out_path);
  return null;
}

async function interactiveLogin(browser, input) {
  const r = input.recipe || {};
  const context = await browser.newContext();
  const page = await context.newPage();
  const closed = new Promise((resolve) => browser.on("disconnected", resolve));
  const timeoutMs = input.timeout_ms || 600000;
  let last = null;
  const snapshot = async () => {
    try {
      last = await context.storageState();
    } catch {
      // the window went away between polls
    }
  };
  try {
    await page.goto(r.url, { waitUntil: "load" });
  } catch {
    await browser.close().catch(() => {});
    return { reason: "login-failed", message: "sign-in failed: could not open the login page" };
  }
  if (!urlAllowed(page.url(), input.url_rules || {})) {
    await browser.close().catch(() => {});
    return BAD_URL;
  }
  process.stderr.write(
    r.success_url_contains
      ? "Sign in in the browser window; it closes by itself once you are in.\n"
      : "Sign in in the browser window, then close the window.\n",
  );
  // Polling alone loses the last second; closing the page or the context snapshots too.
  page.on("close", snapshot);
  context.on("close", snapshot);
  const timer = setInterval(snapshot, 1000);
  let deadline;
  const timedOut = new Promise((resolve) => {
    deadline = setTimeout(() => resolve("timeout"), timeoutMs);
  });
  const matched = r.success_url_contains
    ? page
        .waitForURL((url) => url.toString().includes(r.success_url_contains), { timeout: timeoutMs })
        .then(() => "matched")
        .catch(() => "timeout")
    : new Promise(() => {});
  const outcome = await Promise.race([matched, closed.then(() => "closed"), timedOut]);
  clearInterval(timer);
  clearTimeout(deadline);
  if (outcome === "timeout") {
    await browser.close().catch(() => {});
    return { reason: "login-failed", message: "sign-in failed: the sign-in did not finish in time" };
  }
  if (outcome === "matched") await snapshot();
  await browser.close().catch(() => {});
  if (!last || (!last.cookies.length && !last.origins.length)) return { reason: "login-failed", message: "sign-in failed: no session was captured" };
  save(last, input.out_path);
  return null;
}

async function main() {
  let input;
  try {
    input = JSON.parse(await readStdin());
  } catch {
    return fail("bad-input", "the sign-in script received no valid input", 2);
  }
  const pw = loadPlaywright(input.project_root);
  if (!pw) return fail("playwright-missing", "Playwright is not installed in this project");
  let browser;
  try {
    browser = await pw.chromium.launch({ headless: input.mode !== "interactive" });
    openBrowser = browser;
  } catch {
    return fail("playwright-missing", "the Playwright browser could not start (run `npx playwright install chromium`)");
  }
  const problem =
    input.mode === "interactive" ? await interactiveLogin(browser, input) : await recipeLogin(browser, input);
  await browser.close().catch(() => {});
  if (problem) return fail(problem.reason, problem.message, problem.reason === "invalid-login-url" ? 2 : 3);
  return reply({ ok: true });
}

main().catch(() => fail("login-failed", "sign-in failed unexpectedly"));
