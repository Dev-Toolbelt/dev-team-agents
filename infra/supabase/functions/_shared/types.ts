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
  takeSlot(userId: string): Promise<boolean>;
  touchLastSeen(userId: string, at: Date): Promise<void>;
  markBanned(emailHmacHex: string, reason: string): Promise<void>;
  markTrialConsumed(emailHmacHex: string, startedAt: Date): Promise<void>;
  deleteUser(userId: string): Promise<void>;
}

export interface Deps {
  store: Store;
  verifyJwt(token: string): Promise<AuthedUser | null>;
  banKey: string;
  now(): Date;
}
