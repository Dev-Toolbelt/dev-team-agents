import type { AppConfig, EntitlementStatus, License } from "./types.ts";

export const MAX_TOKEN_LIFETIME_DAYS = 30;
const DAY_SECONDS = 86400;

export interface DerivationInput {
  license: License;
  config: AppConfig;
  identityBanned: boolean;
  trialStartedAt: Date;
  now: Date;
}

export interface Derivation {
  status: EntitlementStatus;
  features: string[];
  trialEndsAt: Date | null;
}

export function deriveEntitlement(input: DerivationInput): Derivation {
  const { license, config, identityBanned, trialStartedAt, now } = input;

  if (license.status === "banned" || identityBanned) {
    return { status: "banned", features: [], trialEndsAt: null };
  }
  if (license.plan === "premium") {
    return { status: "premium", features: license.features, trialEndsAt: null };
  }
  if (!config.trial_enabled) {
    return { status: "active", features: license.features, trialEndsAt: null };
  }

  const trialEndsAt = new Date(trialStartedAt.getTime() + config.trial_days * DAY_SECONDS * 1000);
  if (now.getTime() < trialEndsAt.getTime()) {
    return { status: "trial", features: license.features, trialEndsAt };
  }
  return { status: "trial_expired", features: [], trialEndsAt: null };
}

export function expirySeconds(iat: number, maxOfflineDays: number, trialEndsAt: Date | null): number {
  const days = Math.min(Math.max(Math.trunc(maxOfflineDays), 1), MAX_TOKEN_LIFETIME_DAYS);
  const exp = iat + days * DAY_SECONDS;
  if (trialEndsAt === null) return exp;
  return Math.min(exp, Math.floor(trialEndsAt.getTime() / 1000));
}
