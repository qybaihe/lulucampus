/**
 * Bearer session store — web analogue of iOS AuthManager + Keychain.
 * 401 → mark expired and surface re-auth (G3).
 */

const TOKEN_KEY = "onemore.session.token";
const USER_KEY = "onemore.session.user";
const PENDING_ROUTE_KEY = "onemore.session.pendingRoute";

export type SessionState =
  | { status: "anonymous" }
  | { status: "authenticated"; token: string; user?: SessionUser | null }
  | { status: "expired"; previousToken?: string };

export interface SessionUser {
  user_id?: string;
  display_name?: string;
  campus?: string;
  major?: string;
  [key: string]: unknown;
}

export type SessionListener = (state: SessionState) => void;

export interface SessionStore {
  getState(): SessionState;
  getToken(): string | null;
  setSession(token: string, user?: SessionUser | null): void;
  markExpired(): void;
  clear(): void;
  setPendingRoute(route: string | null): void;
  getPendingRoute(): string | null;
  subscribe(listener: SessionListener): () => void;
}

function readJSON<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function createSessionStore(
  storage: Storage = typeof localStorage !== "undefined"
    ? localStorage
    : ({
        getItem: () => null,
        setItem: () => undefined,
        removeItem: () => undefined,
      } as unknown as Storage),
): SessionStore {
  let state: SessionState = (() => {
    const token = storage.getItem(TOKEN_KEY);
    if (!token) return { status: "anonymous" as const };
    const user = readJSON<SessionUser>(USER_KEY);
    return { status: "authenticated" as const, token, user };
  })();

  const listeners = new Set<SessionListener>();

  const emit = () => {
    for (const l of listeners) l(state);
  };

  return {
    getState: () => state,
    getToken: () =>
      state.status === "authenticated" ? state.token : null,
    setSession(token, user = null) {
      storage.setItem(TOKEN_KEY, token);
      if (user) storage.setItem(USER_KEY, JSON.stringify(user));
      else storage.removeItem(USER_KEY);
      state = { status: "authenticated", token, user };
      emit();
    },
    markExpired() {
      const prev =
        state.status === "authenticated" ? state.token : undefined;
      storage.removeItem(TOKEN_KEY);
      state = { status: "expired", previousToken: prev };
      emit();
    },
    clear() {
      storage.removeItem(TOKEN_KEY);
      storage.removeItem(USER_KEY);
      storage.removeItem(PENDING_ROUTE_KEY);
      state = { status: "anonymous" };
      emit();
    },
    setPendingRoute(route) {
      if (route) storage.setItem(PENDING_ROUTE_KEY, route);
      else storage.removeItem(PENDING_ROUTE_KEY);
    },
    getPendingRoute() {
      return storage.getItem(PENDING_ROUTE_KEY);
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

/** Singleton used by the app entry. Tests should call createSessionStore(). */
export const sessionStore = createSessionStore();
