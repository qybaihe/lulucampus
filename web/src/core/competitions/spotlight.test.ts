import { describe, expect, it } from "vitest";
import {
  hotSeatChip,
  isHotSeat,
  isHotTeam,
  rankCompetitionsForYou,
  recruitGapCount,
  spotlightFitLabel,
} from "./spotlight";

describe("competition spotlight", () => {
  it("treats 很适合你 + exactly one role gap as the hot seat", () => {
    const item = {
      id: "ai",
      taste_fit_label: "很适合你",
      recruit_gap_count: 1,
      recruit_gap_labels: ["设计"],
    };
    expect(isHotSeat(item)).toBe(true);
    expect(hotSeatChip(item)).toBe("正好差一个设计");
  });

  it("promotes a close fit into 很适合你 when it is exactly one seat short", () => {
    const item = {
      id: "chain",
      taste_fit: 0.5317,
      taste_fit_label: "和你有点像",
      recruit_gap_count: 1,
      recruit_gap_labels: ["视觉"],
    };
    expect(isHotSeat(item)).toBe(true);
    expect(spotlightFitLabel(item)).toBe("很适合你");
    expect(hotSeatChip(item)).toBe("正好差一个视觉");
  });

  it("does not light the ring when the fit is only close and several roles are missing", () => {
    expect(
      isHotSeat({
        taste_fit: 0.53,
        taste_fit_label: "和你有点像",
        recruit_gap_count: 2,
        recruit_gap_labels: ["设计", "路演"],
      }),
    ).toBe(false);
  });

  it("does not light a weak close-fit that happens to miss one role", () => {
    expect(
      isHotSeat({
        taste_fit: 0.4,
        taste_fit_label: "和你有点像",
        recruit_gap_count: 1,
        recruit_gap_labels: ["设计"],
      }),
    ).toBe(false);
  });

  it("falls back to recruit hint copy when gap count is missing", () => {
    expect(
      recruitGapCount({
        recruit_hints: ["组队时建议再找会前端的人"],
      }),
    ).toBe(1);
  });

  it("keeps unauthenticated order unchanged", () => {
    const items = [{ id: "a" }, { id: "b" }, { id: "c" }];
    expect(rankCompetitionsForYou(items).map((item) => item.id)).toEqual([
      "a",
      "b",
      "c",
    ]);
  });

  it("lifts the jackpot card above a merely good fit", () => {
    const ranked = rankCompetitionsForYou([
      { id: "close", taste_fit_label: "和你有点像", recruit_gap_count: 0 },
      { id: "good", taste_fit_label: "很适合你", recruit_gap_count: 2 },
      {
        id: "hot",
        taste_fit: 0.53,
        taste_fit_label: "和你有点像",
        recruit_gap_count: 1,
        recruit_gap_labels: ["设计"],
      },
    ]);
    expect(ranked.map((item) => item.id)).toEqual(["hot", "good", "close"]);
  });

  it("marks a team that is one seat short when the competition is a hot fit", () => {
    expect(
      isHotTeam(
        { taste_fit_label: "很适合你", recruit_gap_count: 1 },
        { member_count: 3, target_size: 4 },
      ),
    ).toBe(true);
    expect(
      isHotTeam(
        { taste_fit_label: "很适合你", recruit_gap_count: 1 },
        { member_count: 2, target_size: 4 },
      ),
    ).toBe(false);
  });
});
