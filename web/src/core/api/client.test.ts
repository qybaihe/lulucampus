import { describe, expect, it, vi } from "vitest";
import { APIClient, APIClientError } from "./client";
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
});
