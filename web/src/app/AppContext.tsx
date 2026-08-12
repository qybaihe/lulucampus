import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { APIClient, defaultBaseURL, isLocalAPIBase } from "../core/api/client";
import {
  createRepositories,
  type Repositories,
} from "../core/api/repositories";
import {
  createSessionStore,
  sessionStore as defaultSession,
  type SessionState,
  type SessionStore,
} from "../core/api/session";
import {
  resolveShellMode,
  type ShellMode,
} from "../core/shell/shellMode";

export interface AppContextValue {
  client: APIClient;
  repos: Repositories;
  session: SessionStore;
  sessionState: SessionState;
  shellMode: ShellMode;
  baseURL: string;
}

const AppCtx = createContext<AppContextValue | null>(null);

export function AppProvider({
  children,
  session: sessionOverride,
  baseURL: baseURLOverride,
  fetchImpl,
}: {
  children: ReactNode;
  session?: SessionStore;
  baseURL?: string;
  fetchImpl?: typeof fetch;
}) {
  const session = sessionOverride ?? defaultSession;
  const [sessionState, setSessionState] = useState(session.getState());
  const [width, setWidth] = useState(
    typeof window !== "undefined" ? window.innerWidth : 393,
  );

  useEffect(() => session.subscribe(setSessionState), [session]);

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const baseURL = baseURLOverride ?? defaultBaseURL();
  const shellMode = resolveShellMode(width);

  const value = useMemo(() => {
    // 只有连本机 FastAPI 时才带 DEV_AUTH；yarn dev 打线上接口必须真实登录。
    const devAuthHeader =
      typeof import.meta !== "undefined" &&
      import.meta.env?.DEV &&
      isLocalAPIBase(baseURL)
        ? String(import.meta.env?.VITE_DEV_AUTH ?? "Bearer dev:u_demo_1")
        : null;
    const client = new APIClient({
      baseURL,
      session,
      fetchImpl,
      devAuthHeader,
      onSessionExpired: () => {
        session.setPendingRoute(
          typeof window !== "undefined"
            ? window.location.pathname + window.location.search
            : null,
        );
      },
    });
    return {
      client,
      repos: createRepositories(client),
      session,
      sessionState,
      shellMode,
      baseURL,
    };
  }, [baseURL, session, sessionState, fetchImpl]);

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp(): AppContextValue {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used within AppProvider");
  return ctx;
}

/** For tests that need an isolated session without touching localStorage singleton. */
export function createTestSession(): SessionStore {
  const mem: Record<string, string> = {};
  const storage = {
    getItem: (k: string) => mem[k] ?? null,
    setItem: (k: string, v: string) => {
      mem[k] = v;
    },
    removeItem: (k: string) => {
      delete mem[k];
    },
  } as Storage;
  return createSessionStore(storage);
}
