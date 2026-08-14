import { describe, expect, it } from "vitest";
import {
  EXTRA_COMPOSITE_NODES,
  FIVE_TAB_LABELS,
  FORMAL_NODE_COUNT,
  FORMAL_NODES,
  productionWebRoutes,
  TAB_ROOTS,
  TASTE_IMPORT_ROUTE,
} from "./formalNodes";

describe("formal node registry", () => {
  it("has exactly 74 formal production nodes", () => {
    expect(FORMAL_NODES.length).toBe(FORMAL_NODE_COUNT);
    expect(FORMAL_NODES.length).toBe(74);
    const ids = new Set(FORMAL_NODES.map((n) => n.id));
    expect(ids.size).toBe(74);
  });

  it("includes required feature areas", () => {
    const areas = new Set(FORMAL_NODES.map((n) => n.area));
    for (const a of [
      "auth",
      "today",
      "competitions",
      "intent",
      "gatherings",
      "messages",
      "profile",
      "relations",
      "organizer",
      "shared",
    ]) {
      expect(areas.has(a as never)).toBe(true);
    }
  });

  it("five-tab labels match iOS verbatim", () => {
    expect([...FIVE_TAB_LABELS]).toEqual(["今天", "活动", "差一个", "消息", "我"]);
    expect(TAB_ROOTS.today.label).toBe("今天");
    expect(TAB_ROOTS.competitions.label).toBe("活动");
    expect(TAB_ROOTS.create.label).toBe("差一个");
    expect(TAB_ROOTS.messages.label).toBe("消息");
    expect(TAB_ROOTS.me.label).toBe("我");
  });

  it("production web routes cover formal route nodes + composites + taste", () => {
    const routes = productionWebRoutes();
    const ids = new Set(routes.map((r) => r.id));
    // Tab roots
    expect(ids.has("B1")).toBe(true);
    expect(ids.has("B12")).toBe(true);
    expect(ids.has("D1")).toBe(true);
    expect(ids.has("M1")).toBe(true);
    expect(ids.has("MSG")).toBe(true);
    // Auth
    expect(ids.has("A2")).toBe(true);
    expect(ids.has("A3")).toBe(true);
    // Gatherings / intent / profile
    expect(ids.has("C1")).toBe(true);
    expect(ids.has("E1")).toBe(true);
    expect(ids.has("E14")).toBe(true);
    expect(ids.has("E15")).toBe(true);
    expect(ids.has("O1")).toBe(true);
    expect(ids.has(TASTE_IMPORT_ROUTE.id)).toBe(true);
    expect(EXTRA_COMPOSITE_NODES.map((n) => n.id)).toEqual(["B12.2", "MSG"]);
    // Every production route has a path and a11y id
    for (const r of routes) {
      expect(r.path.startsWith("/")).toBe(true);
      expect(r.a11y.length).toBeGreaterThan(0);
    }
  });
});
