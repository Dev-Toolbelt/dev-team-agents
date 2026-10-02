import { assertEquals } from "jsr:@std/assert@1";
import { deriveEntitlement, expirySeconds } from "./status.ts";
import type { AppConfig, License } from "./types.ts";

const now = new Date("2026-10-02T12:00:00Z");
const day = 86400_000;
const free: License = { plan: "free", status: "active", features: ["x"], trial_started_at: null, ban_reason: null };
const cfg = (o: Partial<AppConfig> = {}): AppConfig => ({ trial_enabled: false, trial_days: 5, max_offline_days: 7, ...o });
const derive = (license: License, config: AppConfig, extra: { identityBanned?: boolean; start?: Date } = {}) =>
  deriveEntitlement({
    license,
    config,
    identityBanned: extra.identityBanned ?? false,
    trialStartedAt: extra.start ?? now,
    now,
  });

Deno.test("trial disabled: everyone is active", () => {
  const d = derive(free, cfg(), { start: new Date(now.getTime() - 400 * day) });
  assertEquals(d.status, "active");
  assertEquals(d.trialEndsAt, null);
});

Deno.test("trial enabled: running trial reports its end", () => {
  const d = derive(free, cfg({ trial_enabled: true }), { start: new Date(now.getTime() - 2 * day) });
  assertEquals(d.status, "trial");
  assertEquals(d.trialEndsAt?.getTime(), now.getTime() + 3 * day);
});

Deno.test("trial enabled: past trial_days is trial_expired without features", () => {
  const d = derive(free, cfg({ trial_enabled: true }), { start: new Date(now.getTime() - 5 * day) });
  assertEquals(d.status, "trial_expired");
  assertEquals(d.features, []);
});

Deno.test("premium wins over an expired trial and keeps features", () => {
  const d = derive({ ...free, plan: "premium" }, cfg({ trial_enabled: true }), {
    start: new Date(now.getTime() - 99 * day),
  });
  assertEquals(d.status, "premium");
  assertEquals(d.features, ["x"]);
});

Deno.test("license ban and identity ban both resolve to banned", () => {
  assertEquals(derive({ ...free, status: "banned" }, cfg()).status, "banned");
  assertEquals(derive(free, cfg(), { identityBanned: true }).status, "banned");
  assertEquals(derive({ ...free, plan: "premium" }, cfg(), { identityBanned: true }).features, []);
});

Deno.test("expiry: iat plus offline days, capped at 30 days", () => {
  assertEquals(expirySeconds(1000, 7, null), 1000 + 7 * 86400);
  assertEquals(expirySeconds(1000, 365, null), 1000 + 30 * 86400);
});

Deno.test("expiry: never beyond the trial end", () => {
  const ends = new Date((1000 + 2 * 86400) * 1000);
  assertEquals(expirySeconds(1000, 7, ends), 1000 + 2 * 86400);
});
