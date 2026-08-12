import { describe, expect, it } from "vitest";
import { createSessionStore } from "./session";

function mem() {
  const store: Record<string, string> = {};
  return {
    getItem: (k: string) => store[k] ?? null,
    setItem: (k: string, v: string) => {
      store[k] = v;
    },
    removeItem: (k: string) => {
      delete store[k];
    },
  } as Storage;
}

describe("session store", () => {
  it("starts anonymous and authenticates with bearer", () => {
    const s = createSessionStore(mem());
    expect(s.getState().status).toBe("anonymous");
    s.setSession("abc", { display_name: "阿哲" });
    expect(s.getState()).toMatchObject({
      status: "authenticated",
      token: "abc",
    });
    expect(s.getToken()).toBe("abc");
  });

  it("markExpired clears token and preserves gate signal", () => {
    const s = createSessionStore(mem());
    s.setSession("tok");
    s.markExpired();
    expect(s.getState().status).toBe("expired");
    expect(s.getToken()).toBeNull();
  });

  it("stores pending route for post-auth recovery", () => {
    const s = createSessionStore(mem());
    s.setPendingRoute("/gathering/x");
    expect(s.getPendingRoute()).toBe("/gathering/x");
    s.setPendingRoute(null);
    expect(s.getPendingRoute()).toBeNull();
  });
});
