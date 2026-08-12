import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { createRepositories } from "../../core/api/repositories";
import { APIClient } from "../../core/api/client";
import { createSessionStore } from "../../core/api/session";

describe("B10 scene_trigger data path", () => {
  it("ships SceneTriggerScreen that reads summary.scene_trigger fields", () => {
    const src = readFileSync(
      join(process.cwd(), "src/screens/today/TodayScreens.tsx"),
      "utf8",
    );
    expect(src).toContain("export function SceneTriggerScreen");
    expect(src).toContain("repos.today.summary");
    expect(src).toContain("scene_trigger");
    expect(src).not.toContain("今晚图书馆 4F 有空档");
    expect(src).not.toContain("与你作业 DDL 重叠");
  });

  it("today.summary + ignoreSceneTrigger hit real FastAPI paths via shipped client", async () => {
    const mem: Record<string, string> = {};
    const session = createSessionStore({
      getItem: (k) => mem[k] ?? null,
      setItem: (k, v) => {
        mem[k] = v;
      },
      removeItem: (k) => {
        delete mem[k];
      },
    } as Storage);
    session.setSession("tok");

    const calls: string[] = [];
    const fetchImpl = async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      if (url.includes("/today/summary")) {
        return new Response(
          JSON.stringify({
            data: {
              scene_trigger: {
                key: "lib-slot",
                title: "服务端标题",
                body: "服务端正文",
                cta_label: "查看",
              },
            },
            meta: {},
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/today/triggers/") && url.includes("/ignore")) {
        return new Response(JSON.stringify({ data: {}, meta: {} }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ error: { code: "X", message: "no" } }), {
        status: 404,
      });
    };

    const client = new APIClient({
      baseURL: "http://example.test",
      session,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const repos = createRepositories(client);
    const summary = await repos.today.summary();
    expect(summary.scene_trigger?.title).toBe("服务端标题");
    expect(summary.scene_trigger?.body).toBe("服务端正文");
    expect(summary.scene_trigger?.key).toBe("lib-slot");
    await repos.today.ignoreSceneTrigger("lib-slot");
    expect(calls.some((c) => c.includes("/today/summary"))).toBe(true);
    expect(
      calls.some((c) => c.includes("/today/triggers/lib-slot/ignore")),
    ).toBe(true);
  });
});
