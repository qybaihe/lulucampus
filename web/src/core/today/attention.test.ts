import { describe, expect, it } from "vitest";
import { attentionItems, pathFromAttentionLink } from "./attention";

describe("today attention for messages tab", () => {
  it("keeps one row when a gathering preview and its action share an id", () => {
    const items = attentionItems([
      {
        gathering_id: "g1",
        type: "authorization",
        title: "数模组队差编程",
        deep_link: "onemore://gathering/g1",
      },
      {
        action_id: "a1",
        gathering_id: "g1",
        type: "authorization",
        title: "数模组队差编程",
        deep_link: "onemore://action/a1",
      },
    ]);
    expect(items).toHaveLength(1);
    expect(items[0]?.title).toBe("「数模组队差编程」等待核对");
    expect(items[0]?.deepLink).toBe("onemore://gathering/g1");
  });

  it("uses confirmation copy and maps deep links", () => {
    const items = attentionItems([
      {
        gathering_id: "g2",
        type: "confirmation",
        from_name: "周衡",
        deep_link: "onemore://gathering/g2",
      },
    ]);
    expect(items[0]?.title).toBe("周衡 有一个局等待你确认");
    expect(items[0]?.badge).toBe("差你 1 票");
    expect(pathFromAttentionLink("onemore://gathering/g2")).toBe("/gathering/g2");
  });
});
