import { describe, expect, it, vi } from "vitest";
import { APIClient, APIClientError, defaultBaseURL, isLocalAPIBase } from "./client";
import { createSessionStore } from "./session";

function memorySession() {
  const mem: Record<string, string> = {};
  return createSessionStore({
    getItem: (k) => mem[k] ?? null,
    setItem: (k, v) => {
      mem[k] = v;
    },
    removeItem: (k) => {
      delete mem[k];
    },
  } as Storage);
}

describe("APIClient", () => {
  it("unwraps data from success envelope", async () => {
    const session = memorySession();
    session.setSession("tok-1");
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify({ data: { name: "数模" }, meta: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json", "X-Request-ID": "rid-1" },
      }),
    );
    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const data = await client.get<{ name: string }>("/competitions/1");
    expect(data.name).toBe("数模");
    expect(client.lastRequestId).toBe("rid-1");
    expect(fetchImpl).toHaveBeenCalled();
    const call = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(call[1].headers).toMatchObject({
      Authorization: "Bearer tok-1",
    });
  });

  it("maps error envelope to APIClientError.server", async () => {
    const session = memorySession();
    session.setSession("tok-1");
    const fetchImpl = vi.fn(async () =>
      new Response(
        JSON.stringify({
          error: { code: "FORBIDDEN", message: "禁止", details: {} },
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    await expect(client.get("/secret")).rejects.toMatchObject({
      kind: "server",
      message: "禁止",
    });
  });

  it("401 marks session expired and throws sessionExpired", async () => {
    const session = memorySession();
    session.setSession("old");
    const onExpired = vi.fn();
    const fetchImpl = vi.fn(async () =>
      new Response(
        JSON.stringify({
          error: { code: "UNAUTHORIZED", message: "失效" },
        }),
        { status: 401, headers: { "Content-Type": "application/json" } },
      ),
    );
    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
      onSessionExpired: onExpired,
    });
    await expect(client.get("/today/summary")).rejects.toBeInstanceOf(
      APIClientError,
    );
    try {
      await client.get("/today/summary");
    } catch (e) {
      expect((e as APIClientError).kind).toBe("sessionExpired");
    }
    expect(session.getState().status).toBe("expired");
    expect(onExpired).toHaveBeenCalled();
  });

  it("treats only loopback hosts as local API bases", () => {
    expect(isLocalAPIBase("http://127.0.0.1:8000")).toBe(true);
    expect(isLocalAPIBase("http://localhost:8000")).toBe(true);
    expect(isLocalAPIBase("http://42.194.219.172/onemore/api")).toBe(false);
    expect(isLocalAPIBase("https://lulu.classby.cn/onemore/api")).toBe(false);
    expect(isLocalAPIBase("/onemore/api")).toBe(false);
  });

  it("defaults to the shared production API", () => {
    expect(defaultBaseURL()).toContain("onemore/api");
    expect(isLocalAPIBase(defaultBaseURL())).toBe(false);
  });
});
