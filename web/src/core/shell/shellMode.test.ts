import { describe, expect, it } from "vitest";
import {
  DESKTOP_SHELL_MIN_WIDTH,
  resolveShellMode,
  shouldShowPhoneChrome,
} from "./shellMode";

describe("resolveShellMode", () => {
  it("uses desktop phone frame at wide widths", () => {
    expect(resolveShellMode(1024)).toBe("desktop-frame");
    expect(resolveShellMode(DESKTOP_SHELL_MIN_WIDTH)).toBe("desktop-frame");
    expect(shouldShowPhoneChrome("desktop-frame")).toBe(true);
  });

  it("uses mobile full-bleed at phone widths", () => {
    expect(resolveShellMode(430)).toBe("mobile-fullbleed");
    expect(resolveShellMode(375)).toBe("mobile-fullbleed");
    expect(resolveShellMode(DESKTOP_SHELL_MIN_WIDTH - 1)).toBe(
      "mobile-fullbleed",
    );
    expect(shouldShowPhoneChrome("mobile-fullbleed")).toBe(false);
  });

  it("degrades invalid widths to mobile full-bleed", () => {
    expect(resolveShellMode(Number.NaN)).toBe("mobile-fullbleed");
    expect(resolveShellMode(-1)).toBe("mobile-fullbleed");
  });
});
