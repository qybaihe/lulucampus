import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { APIClient } from "../../core/api/client";
import {
  createRepositories,
  getOrCreateDeviceInstallId,
} from "../../core/api/repositories";
import { createSessionStore } from "../../core/api/session";

function memSession() {
  const store: Record<string, string> = {};
  return createSessionStore({
    getItem: (k) => store[k] ?? null,
    setItem: (k, v) => {
      store[k] = v;
    },
    removeItem: (k) => {
      delete store[k];
    },
  } as Storage);
}

describe("auth flow — iOS-aligned FastAPI contract", () => {
  it("uses 噜噜成局 as the master brand while keeping 差一个 as the core action", () => {
    const auth = readFileSync(
      join(process.cwd(), "src/screens/auth/AuthScreens.tsx"),
      "utf8",
    );
    const html = readFileSync(join(process.cwd(), "index.html"), "utf8");
    expect(auth).toContain("噜噜成局");
    expect(auth).toContain("差一个，就成局");
    expect(auth).toContain("AppBrand.agentName");
    expect(html).toContain("<title>噜噜成局</title>");
    const brand = readFileSync(join(process.cwd(), "src/core/brand.ts"), "utf8");
    expect(brand).toContain('agentName: "Lulu Hermes"');
  });

  it("AuthScanScreen uses server qr_image_data_url and does not hard-code fake QR path", () => {
    const src = readFileSync(
      join(process.cwd(), "src/screens/auth/AuthScreens.tsx"),
      "utf8",
    );
    const repos = readFileSync(
      join(process.cwd(), "src/core/api/repositories.ts"),
      "utf8",
    );
    expect(src).toContain("qr_image_data_url");
    expect(src).toContain("redemption_token");
    expect(src).toContain("pollSession");
    // 扫码为登录后绑定：SUCCESS 后 redeem，再进授权/今天
    expect(src).toContain("markCampusGatePassed");
    expect(src).toContain("repos.auth.redeem");
    expect(src).toContain("/auth/grants");
    expect(repos).toContain("X-Login-Redemption");
    expect(repos).toContain("redeem");
    // Must not rely only on a static decorative SVG without server data
    expect(src).toContain('data-od-id="auth-qr-image"');
    // grant scopes match iOS
    expect(src).toContain("timetable");
    expect(src).toContain("agent_booking");
    expect(src).toContain("setGrant");
    expect(src).toContain("setSocialEnabled");
    expect(src).toContain("/auth/taste");
    expect(src).toContain("first-use-skip-taste");
    expect(src).toContain("repos.taste.fromLink");
    expect(src).toContain("暂时跳过，稍后再贴");
    expect(src).toContain("onemore.firstuse.tastePending.v1");
    // 选校引导
    expect(src).toContain("中山大学");
    expect(src).toContain("onboarding-school-");
    expect(src).toContain('id: "sysu"');
  });

  it("startSession → poll with redemption header → redeem returns access_token", async () => {
    const session = memSession();
    const calls: Array<{ url: string; method: string; headers: HeadersInit }> =
      [];
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ url, method, headers: init?.headers ?? {} });
      if (url.endsWith("/auth/session") && method === "POST") {
        return new Response(
          JSON.stringify({
            data: {
              id: "sess-1",
              user_id: "u1",
              status: "WAITING_SCAN",
              qr_image_data_url:
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
              deep_link: "onemore://auth/scan/sess-1",
              expires_at: new Date(Date.now() + 200000).toISOString(),
              redemption_token: "r".repeat(40),
              error_category: null,
            },
            meta: { poll_after_seconds: 2 },
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/auth/session/sess-1") && method === "GET") {
        return new Response(
          JSON.stringify({
            data: {
              id: "sess-1",
              user_id: "u1",
              status: "SUCCESS",
              qr_image_data_url:
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
              deep_link: null,
              expires_at: new Date(Date.now() + 200000).toISOString(),
              error_category: null,
            },
            meta: {},
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/redeem") && method === "POST") {
        const body = JSON.parse(String(init?.body ?? "{}"));
        expect(body.redemption_token).toHaveLength(40);
        return new Response(
          JSON.stringify({ data: { access_token: "bearer-shared-with-ios" } }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response(JSON.stringify({ error: { code: "X", message: url } }), {
        status: 404,
      });
    });

    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const repos = createRepositories(client);

    const started = await repos.auth.startSession({
      device_install_id: "install-web-1",
    });
    expect(started.id).toBe("sess-1");
    expect(started.redemption_token).toBeTruthy();
    expect(started.qr_image_data_url).toContain("data:image/png");

    const polled = await repos.auth.pollSession(
      started.id,
      started.redemption_token!,
    );
    expect(polled.status).toBe("SUCCESS");
    const pollCall = calls.find((c) => c.method === "GET");
    const headers = pollCall?.headers as Record<string, string>;
    expect(headers["X-Login-Redemption"] || headers["x-login-redemption"]).toBe(
      started.redemption_token,
    );

    const redeemed = await repos.auth.redeem(
      started.id,
      started.redemption_token!,
    );
    expect(redeemed.access_token).toBe("bearer-shared-with-ios");
    session.setSession(redeemed.access_token);
    expect(session.getToken()).toBe("bearer-shared-with-ios");
  });

  it("setGrant posts one scope at a time like iOS", async () => {
    const session = memSession();
    session.setSession("tok");
    const bodies: unknown[] = [];
    const fetchImpl = vi.fn(async (_u: RequestInfo | URL, init?: RequestInit) => {
      bodies.push(JSON.parse(String(init?.body ?? "{}")));
      return new Response(
        JSON.stringify({
          data: {
            scope: "timetable",
            granted: true,
            granted_at: new Date().toISOString(),
            revoked_at: null,
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });
    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const repos = createRepositories(client);
    await repos.auth.setGrant("timetable", true);
    expect(bodies[0]).toEqual({ scope: "timetable", granted: true });
  });

  it("device install id is stable", () => {
    const a = getOrCreateDeviceInstallId();
    const b = getOrCreateDeviceInstallId();
    expect(a).toBe(b);
    expect(a.length).toBeGreaterThan(8);
  });
});
