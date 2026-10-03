import type { AppConfig, AuthedUser, Deps, License, Store } from "./types.ts";

export const NOW = new Date("2026-10-02T12:00:00Z");

export interface FakeState {
  license: License | null;
  config: AppConfig;
  banned: Set<string>;
  consumed: Map<string, Date>;
  slots: number;
  deleted: string[];
  calls: string[];
}

export function fakeState(over: Partial<FakeState> = {}): FakeState {
  return {
    license: { plan: "free", status: "active", features: [], trial_started_at: null, ban_reason: null },
    config: { trial_enabled: false, trial_days: 5, max_offline_days: 7 },
    banned: new Set(),
    consumed: new Map(),
    slots: 1000,
    deleted: [],
    calls: [],
    ...over,
  };
}

export function fakeStore(s: FakeState): Store {
  return {
    getLicense: () => Promise.resolve(s.license),
    getConfig: () => Promise.resolve(s.config),
    isBanned: (h) => Promise.resolve(s.banned.has(h)),
    getTrialConsumed: (h) => Promise.resolve(s.consumed.get(h) ?? null),
    setTrialStarted: (_u, at) => {
      if (s.license) s.license = { ...s.license, trial_started_at: at };
      return Promise.resolve();
    },
    takeSlot: () => Promise.resolve({ allowed: s.slots-- > 0, retryAfter: 1234 }),
    touchLastSeen: () => Promise.resolve(),
    markBanned: (h) => {
      s.banned.add(h);
      s.calls.push("markBanned");
      return Promise.resolve();
    },
    markTrialConsumed: (h, at) => {
      if (!s.consumed.has(h)) s.consumed.set(h, at);
      s.calls.push("markTrialConsumed");
      return Promise.resolve();
    },
    deleteUser: (id) => {
      s.deleted.push(id);
      s.calls.push("deleteUser");
      return Promise.resolve();
    },
    banUser: (id) => {
      s.calls.push("banUser:" + id);
      return Promise.resolve(USER.email);
    },
  };
}

export const USER: AuthedUser = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "Person@Example.com",
  amr: [{ method: "otp", timestamp: Math.floor(NOW.getTime() / 1000) - 30 }],
};

export function fakeDeps(s: FakeState, user: AuthedUser | null = USER): Deps {
  return {
    store: fakeStore(s),
    verifyJwt: (t) => Promise.resolve(t === "good" ? user : null),
    banKey: "test-pepper",
    now: () => NOW,
  };
}

export function req(method: string, token: string | null, body?: unknown): Request {
  const headers = new Headers();
  if (token) headers.set("authorization", `Bearer ${token}`);
  return new Request("http://localhost/fn", {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
