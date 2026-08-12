import type { ReactNode } from "react";
import type { ShellMode } from "../../core/shell/shellMode";
import { shouldShowPhoneChrome } from "../../core/shell/shellMode";

export function PhoneFrame({
  mode,
  children,
}: {
  mode: ShellMode;
  children: ReactNode;
}) {
  const showChrome = shouldShowPhoneChrome(mode);

  if (!showChrome) {
    return (
      <div
        className="mobile-fullbleed"
        data-shell="mobile-fullbleed"
        data-od-id="screen-root"
      >
        {children}
      </div>
    );
  }

  return (
    <div className="stage" data-shell="desktop-frame">
      <div className="phone" data-od-id="iphone-shell">
        <div className="dynamic-island" aria-hidden />
        <div className="statusbar">
          <span>9:41</span>
          <span className="sb-icons" aria-hidden>
            <svg width="17" height="12" viewBox="0 0 17 12">
              <rect x="0" y="3" width="3" height="9" rx="0.5" fill="currentColor" />
              <rect x="4.5" y="2" width="3" height="10" rx="0.5" fill="currentColor" />
              <rect x="9" y="0.5" width="3" height="11.5" rx="0.5" fill="currentColor" />
              <rect
                x="13.5"
                y="0"
                width="3"
                height="12"
                rx="0.5"
                fill="currentColor"
                opacity="0.35"
              />
            </svg>
          </span>
        </div>
        <div className="screen" id="screen-root" data-od-id="screen-root">
          {children}
        </div>
        <div className="home-indicator" aria-hidden />
      </div>
    </div>
  );
}
