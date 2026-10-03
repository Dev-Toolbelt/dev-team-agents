export type EntitlementStatus = "active" | "trial" | "trial_expired" | "premium" | "banned";

export interface License {
  plan: "free" | "premium";
  status: "active" | "banned";
  features: string[];
  trial_started_at: Date | null;
  ban_reason: string | null;
}

export interface AppConfig {
  trial_enabled: boolean;
  trial_days: number;
  max_offline_days: number;
}

export interface AuthedUser {
  id: string;
  email: string | null;
  amr: { method: string; timestamp: number }[];
}

export interface Store {
  getLicense(userId: string): Promise<License | null>;
  getConfig(): Promise<AppConfig>;
  isBanned(emailHmacHex: string): Promise<boolean>;
  getTrialConsumed(emailHmacHex: string): Promise<Date | null>;
  setTrialStarted(userId: string, at: Date): Promise<void>;
  takeSlot(userId: string): Promise<SlotResult>;
  touchLastSeen(userId: string, at: Date): Promise<void>;
  markBanned(emailHmacHex: string, reason: string): Promise<void>;
  markTrialConsumed(emailHmacHex: string, startedAt: Date): Promise<void>;
  deleteUser(userId: string): Promise<void>;
  banUser(userId: string, reason: string): Promise<string | null>;
}

export interface SlotResult {
  allowed: boolean;
  retryAfter: number;
}

/** The auth service could not answer (not "the token is bad"): the caller returns 503. */
export class AuthUnavailable extends Error {
  override name = "AuthUnavailable";
}

export interface Deps {
  store: Store;
  verifyJwt(token: string): Promise<AuthedUser | null>;
  banKey: string;
  now(): Date;
}
