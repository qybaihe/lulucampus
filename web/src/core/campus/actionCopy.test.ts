import { describe, expect, it } from "vitest";
import { authorizationLine, makeCampusActionCopy } from "./actionCopy";

describe("campus action copy", () => {
  it("turns a gym preview into Chinese title, date, and facts", () => {
    const copy = makeCampusActionCopy({
      action_name: "gym.book_preview",
      status: "previewed",
      params: {
        date: "2026-08-13",
        end: "21:00",
        start: "19:00",
        venue: "南校园",
        venue_type: "羽毛球",
      },
      preview_snapshot: {
        source: "peer_overlap_template",
        action: "gym.book_preview",
        params: {
          date: "2026-08-13",
          venue: "南校园",
          venue_type: "羽毛球",
        },
      },
    });
    expect(copy.title).toBe("预约羽毛球");
    expect(copy.headline).toBe("南校园 · 羽毛球");
    expect(copy.timeLine).toContain("8月13日");
    expect(copy.timeLine).toContain("星期四");
    expect(copy.timeLine).toContain("19:00 – 21:00");
    expect(copy.statusLabel).toBe("时段参考");
    expect(copy.sticker).toBe("badminton.png");
    expect(copy.facts.map((fact) => fact.label)).toEqual([
      "项目",
      "校区",
      "日期",
      "时段",
    ]);
    const blob = [copy.title, copy.headline, copy.timeLine, ...copy.facts.map((f) => f.label + f.value)].join();
    expect(blob).not.toContain("gym.book_preview");
    expect(blob).not.toContain("peer_overlap_template");
    expect(blob).not.toContain("params.");
  });

  it("hides technical tokens for room previews", () => {
    const copy = makeCampusActionCopy({
      action_name: "room.reserve_preview",
      status: "previewed",
      params: { room: "A101", date: "2026-08-13", start: "14:00", end: "16:00" },
    });
    expect(copy.title).toBe("预约研讨室");
    expect(copy.headline).toContain("A101");
    expect(copy.facts.some((fact) => fact.label === "房间" && fact.value === "A101")).toBe(true);
  });

  it("writes a short authorization line", () => {
    expect(authorizationLine(0, 1)).toBe("提交前再确认一遍");
    expect(authorizationLine(1, 3)).toBe("1 / 3 位已核对");
    expect(authorizationLine(3, 3)).toBe("大家都核对过了");
  });
});
