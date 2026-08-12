/**
 * Desktop phone-frame vs mobile full-bleed decision.
 * Matches design mobile-ios.html shell: phone is always mobile-width;
 * on wide viewports we show chrome; on narrow we go full-bleed.
 */

export type ShellMode = "desktop-frame" | "mobile-fullbleed";

/** Breakpoint at which the phone bezel appears (inclusive). */
export const DESKTOP_SHELL_MIN_WIDTH = 768;

/** Phone content width used inside the bezel (iPhone 15 logical). */
export const PHONE_CONTENT_WIDTH = 393;
export const PHONE_CONTENT_HEIGHT = 852;

export function resolveShellMode(viewportWidth: number): ShellMode {
  if (!Number.isFinite(viewportWidth) || viewportWidth < 0) {
    return "mobile-fullbleed";
  }
  return viewportWidth >= DESKTOP_SHELL_MIN_WIDTH
    ? "desktop-frame"
    : "mobile-fullbleed";
}

export function shouldShowPhoneChrome(mode: ShellMode): boolean {
  return mode === "desktop-frame";
}
