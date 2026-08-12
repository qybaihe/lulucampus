import { describe, expect, it } from "vitest";
import { gapCountOf, seatsFromGathering, type Gathering } from "./repositories";

describe("seatsFromGathering", () => {
  it("uses only server required_roles and never invents role names", () => {
    const g: Gathering = {
      id: "g1",
      required_roles: ["建模", "编程", "写作"],
      member_count: 2,
      target_size: 3,
      participants: [{ role: "建模" }, { role: "编程" }],
    };
    const seats = seatsFromGathering(g);
    expect(seats.map((s) => s.role)).toEqual(["建模", "编程", "写作"]);
    expect(seats.filter((s) => s.state === "gap")).toHaveLength(1);
    expect(seats.find((s) => s.role === "写作")?.state).toBe("gap");
  });

  it("returns empty when server provides no size and no roles", () => {
    const seats = seatsFromGathering({ id: "g2" });
    expect(seats).toEqual([]);
  });

  it("anonymous filled/gap only when target_size known without role names", () => {
    const seats = seatsFromGathering({
      id: "g3",
      target_size: 3,
      member_count: 1,
    });
    expect(seats).toHaveLength(3);
    expect(seats[0].state).toBe("filled");
    expect(seats[1].state).toBe("gap");
    // labels are generic, not invented professional roles
    expect(seats.every((s) => s.role === "已就位" || s.role === "空位")).toBe(
      true,
    );
  });
});

describe("gapCountOf", () => {
  it("prefers server gap_count", () => {
    expect(gapCountOf({ id: "x", gap_count: 2, target_size: 9, member_count: 1 })).toBe(2);
  });

  it("derives from target and member_count", () => {
    expect(gapCountOf({ id: "x", target_size: 4, member_count: 1 })).toBe(3);
  });
});
