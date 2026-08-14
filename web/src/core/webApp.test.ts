import { describe, expect, it } from "vitest";
import { joinWebAppURL } from "./webApp";

describe("joinWebAppURL", () => {
  it("keeps same-origin paths when origin is empty", () => {
    expect(joinWebAppURL(undefined)).toBe("/app");
    expect(joinWebAppURL("")).toBe("/app");
    expect(joinWebAppURL("   ", "/me")).toBe("/me");
  });

  it("joins the Pages landing to the origin product app", () => {
    expect(joinWebAppURL("https://lulu.classby.cn/onemore")).toBe(
      "https://lulu.classby.cn/onemore/app",
    );
    expect(joinWebAppURL("https://lulu.classby.cn/onemore/", "/auth")).toBe(
      "https://lulu.classby.cn/onemore/auth",
    );
  });
});
