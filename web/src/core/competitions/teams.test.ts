import { describe, expect, it } from "vitest";
import { gapDescription, recruitingHeadline, teamFilled, teamMissingCount } from "./teams";

describe("competition recruiting teams", () => {
  it("renders 2/3 and a single missing role as 差一个建模", () => {
    const team = {
      id: "t-1",
      member_count: 2,
      target_size: 3,
      missing_count: 1,
      missing_roles: ["modeling"],
      filled_roles: ["编程", "写作"],
    };
    expect(teamFilled(team)).toBe(2);
    expect(teamMissingCount(team)).toBe(1);
    expect(gapDescription(team)).toBe("差一个建模");
  });

  it("joins multiple missing roles", () => {
    expect(
      gapDescription({
        id: "t-2",
        member_count: 1,
        target_size: 3,
        missing_count: 2,
        missing_roles: ["modeling", "paper_writing"],
      }),
    ).toBe("还差 2 个角色：建模、写作");
  });

  it("falls back to seat count when roles are absent", () => {
    expect(
      gapDescription({
        id: "t-3",
        member_count: 1,
        target_size: 3,
        missing_count: 2,
        missing_roles: [],
        required_roles: [],
      }),
    ).toBe("还差 2 人");
  });

  it("names the recruiting headline from the live team count", () => {
    expect(recruitingHeadline(3)).toBe("有 3 支队伍正在招人");
    expect(recruitingHeadline(0)).toBe("暂时还没有队伍在招人");
  });
});
