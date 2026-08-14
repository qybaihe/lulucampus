import { describe, expect, it } from "vitest";
import {
  busDayKind,
  campusShortLabel,
  findBusRoute,
  nextBusDeparture,
} from "./busSchedule";
import { sectionTime } from "./sectionTimes";
import {
  parseTrustRequirement,
  trustCapabilityTitle,
  trustLevelRank,
} from "./trustRequirement";
import { APIClientError } from "../api/client";
import { startOfWeekMonday, weekdayLabel, gridTitle } from "./weekSchedule";
import { CAMPUS_HOME_TOOLS } from "./todayTools";
import {
  splitTimeRange,
  timelineKindLabel,
  timelinePhase,
} from "./dayTimeline";

describe("campus bus schedule", () => {
  it("looks up east→north workday departures and next bus", () => {
    const route = findBusRoute("东校园", "北校园");
    expect(route?.fromStation).toContain("兰园");
    const next = nextBusDeparture(
      route!,
      "工作日",
      new Date("2026-08-13T09:00:00"),
    );
    expect(next?.time).toBe("10:00");
  });

  it("treats weekend as 节假日", () => {
    expect(busDayKind(new Date("2026-08-15T10:00:00"))).toBe("节假日");
    expect(busDayKind(new Date("2026-08-13T10:00:00"))).toBe("工作日");
  });

  it("shortens campus labels like iOS picker", () => {
    expect(campusShortLabel("东校园")).toBe("东");
    expect(campusShortLabel("珠海校区")).toBe("珠海");
  });
});

describe("section times", () => {
  it("returns verified 2026 fall section 1", () => {
    expect(sectionTime(1)).toEqual(["08:00", "08:45"]);
    expect(sectionTime(11)).toEqual(["20:50", "21:35"]);
  });
});

describe("trust requirement", () => {
  it("parses TRUST_LEVEL_REQUIRED envelope details", () => {
    const error = new APIClientError("server", "信任等级不够", {
      body: {
        code: "TRUST_LEVEL_REQUIRED",
        message: "需要 T2 才能加入",
        details: { required_level: "T2", capability: "duo_gathering" },
      },
    });
    const ctx = parseTrustRequirement(error, { kind: "gathering", id: "g1" });
    expect(ctx?.requiredLevel).toBe("T2");
    expect(trustCapabilityTitle(ctx?.capability)).toBe("双人高承诺局");
    expect(trustLevelRank("T2")).toBeGreaterThan(trustLevelRank("T0"));
  });
});

describe("week schedule helpers", () => {
  it("anchors Monday and strips course category prefixes", () => {
    const monday = startOfWeekMonday(new Date("2026-08-13T12:00:00"));
    expect(monday.getDay()).toBe(1);
    expect(weekdayLabel(monday)).toBe("周一");
    expect(gridTitle("本 (专必) 高等数学")).toBe("高等数学");
  });
});

describe("today home campus tools", () => {
  it("keeps the same four tiles as iOS TodayView", () => {
    expect(CAMPUS_HOME_TOOLS.map((tool) => tool.label)).toEqual([
      "日程",
      "活动",
      "班车",
      "我的局",
    ]);
    expect(CAMPUS_HOME_TOOLS).toHaveLength(4);
  });
});

describe("today timeline phases", () => {
  it("marks current, past, and upcoming from start/end", () => {
    const now = new Date("2026-08-13T10:30:00").getTime();
    expect(
      timelinePhase(
        { start_at: "2026-08-13T10:00:00", end_at: "2026-08-13T11:00:00" },
        now,
      ),
    ).toBe("current");
    expect(
      timelinePhase(
        { start_at: "2026-08-13T08:00:00", end_at: "2026-08-13T09:40:00" },
        now,
      ),
    ).toBe("past");
    expect(
      timelinePhase(
        { start_at: "2026-08-13T14:00:00", end_at: "2026-08-13T15:40:00" },
        now,
      ),
    ).toBe("upcoming");
    expect(splitTimeRange("08:00–09:40")).toEqual(["08:00", "09:40"]);
    expect(timelineKindLabel("gathering")).toBe("活动");
  });
});
