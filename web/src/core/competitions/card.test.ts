import { describe, expect, it } from "vitest";
import {
  competitionSticker,
  competitionTitleClass,
  deadlineBadge,
} from "./card";

describe("competitionSticker", () => {
  it("uses flask for research tracks", () => {
    expect(competitionSticker({ name: "挑战杯", tracks: ["学术科研"] })).toBe(
      "flask.png",
    );
  });
  it("uses bulb for entrepreneurship", () => {
    expect(competitionSticker({ name: "互联网+创新创业" })).toBe("bulb.png");
  });
  it("defaults to trophy", () => {
    expect(competitionSticker({ name: "ACM 程序设计" })).toBe("trophy.png");
  });
});

describe("competitionTitleClass", () => {
  it("steps down by character count", () => {
    expect(competitionTitleClass("短标题")).toBe("t-t3");
    expect(competitionTitleClass("这是一个十三字以上的赛事名")).toBe("t-call");
    expect(competitionTitleClass("这是一个特别特别长的赛事名称需要降到脚注字号")).toBe(
      "t-foot",
    );
  });
});

describe("deadlineBadge", () => {
  const noon = new Date("2026-08-13T12:00:00").getTime();
  it("marks today and 3-day window as gap", () => {
    expect(deadlineBadge("2026-08-13T18:00:00", noon)?.label).toBe("今天截止");
    expect(deadlineBadge("2026-08-16T18:00:00", noon)).toEqual({
      kind: "gap",
      label: "还剩 3 天截止",
    });
  });
  it("uses quiet clock copy after 3 days", () => {
    const badge = deadlineBadge("2026-08-20T18:00:00", noon);
    expect(badge?.kind).toBe("quiet");
    expect(badge?.label).toContain("还剩 7 天");
  });
});
