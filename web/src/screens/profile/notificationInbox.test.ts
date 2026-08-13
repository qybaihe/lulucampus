import { describe, expect, it } from "vitest";
import {
  categoryEnabled,
  categoryLabel,
  notificationSummary,
  pathFromDeepLink,
  pathFromNotification,
  relativeTimeLabel,
} from "./notificationInbox";

describe("notification inbox helpers", () => {
  it("maps campus and gathering deep links to web routes", () => {
    expect(pathFromDeepLink("onemore://screen/B3")).toBe("/today/timetable");
    expect(pathFromDeepLink("onemore://screen/B4")).toBe("/today/assignments");
    expect(pathFromDeepLink("onemore://gathering/g-1/space")).toBe("/gathering/g-1");
    expect(pathFromDeepLink("onemore://channel/c-1")).toBe("/channel/c-1");
    expect(pathFromDeepLink("onemore://goal/rel-1")).toBe("/goal/rel-1");
    expect(
      pathFromNotification({
        payload: {
          summary: "会话有新消息",
          channel_id: "c-9",
        },
      }),
    ).toBe("/channel/c-9");
  });

  it("keeps category filters and human summaries", () => {
    expect(categoryLabel("schedule_reminders")).toBe("日程");
    expect(categoryLabel("gathering_updates")).toBe("成局");
    expect(
      notificationSummary({ summary: "「高数」还有 30 分钟就要上课" }, "课表快到了"),
    ).toBe("「高数」还有 30 分钟就要上课");
    expect(
      categoryEnabled({ schedule_reminders: false, gathering_updates: true }, "schedule_reminders"),
    ).toBe(false);
    expect(categoryEnabled({ gathering_updates: true }, "gathering_updates")).toBe(true);
    expect(relativeTimeLabel(new Date(Date.now() - 30_000).toISOString()).length).toBeGreaterThan(0);
  });
});
