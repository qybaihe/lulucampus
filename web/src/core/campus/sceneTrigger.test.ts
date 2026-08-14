import { describe, expect, it } from "vitest";
import { normalizeSceneTrigger } from "./sceneTrigger";

describe("normalizeSceneTrigger", () => {
  it("maps FastAPI scene_key/text/context.title", () => {
    const view = normalizeSceneTrigger({
      scene_key: "assignment:a1",
      kind: "ddl_sprint",
      text: "今晚开一个 90 分钟冲刺局吗？",
      context: { assignment_id: "a1", title: "软件工程迭代作业" },
    });
    expect(view).toEqual({
      key: "assignment:a1",
      title: "软件工程迭代作业",
      body: "今晚开一个 90 分钟冲刺局吗？",
      cta_label: undefined,
    });
  });

  it("keeps legacy key/title/body", () => {
    const view = normalizeSceneTrigger({
      key: "lib-slot",
      title: "服务端标题",
      body: "服务端正文",
      cta_label: "查看",
    });
    expect(view?.key).toBe("lib-slot");
    expect(view?.title).toBe("服务端标题");
    expect(view?.body).toBe("服务端正文");
    expect(view?.cta_label).toBe("查看");
  });

  it("returns null without a key", () => {
    expect(normalizeSceneTrigger({ text: "x" })).toBeNull();
    expect(normalizeSceneTrigger(null)).toBeNull();
  });
});
