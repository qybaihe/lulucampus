/**
 * @vitest-environment jsdom
 * Post-mount DOM proof: five-tab labels + phone-frame chrome.
 */
Object.defineProperty(window, "matchMedia", {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }),
});

import { cleanup, render, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AppProvider, createTestSession } from "../app/AppContext";
import App from "../App";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function mockFetchOk() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    let body: unknown = { data: {}, meta: {} };
    if (url.includes("/today/summary")) {
      body = { data: { timeline: [], tools: [] }, meta: {} };
    } else if (url.includes("/competitions")) {
      body = { data: [], meta: {} };
    } else if (url.includes("/gatherings")) {
      body = { data: [], meta: {} };
    } else if (url.includes("/events")) {
      body = { data: [], meta: {} };
    } else if (url.includes("/me/privacy")) {
      body = { data: { social_enabled: true }, meta: {} };
    } else if (url.includes("/auth/me") || url.includes("/trust/me")) {
      body = { data: { display_name: "测试同学", level: "2" }, meta: {} };
    } else if (url.includes("/relations")) {
      body = { data: [], meta: {} };
    }
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
}

function renderAt(path: string, width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  const session = createTestSession();
  session.setSession("test-token", { display_name: "测试同学" });
  const fetchImpl = mockFetchOk() as unknown as typeof fetch;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppProvider
        session={session}
        baseURL="http://example.test"
        fetchImpl={fetchImpl}
      >
        <App />
      </AppProvider>
    </MemoryRouter>,
  );
}

describe("mounted shell DOM evidence", () => {
  it("desktop width shows phone-frame chrome (iphone-shell)", () => {
    const { container } = renderAt("/today", 1024);
    expect(container.querySelector('[data-shell="desktop-frame"]')).toBeTruthy();
    expect(container.querySelector('[data-od-id="iphone-shell"]')).toBeTruthy();
  });

  it("mobile width is full-bleed without phone chrome", () => {
    const { container } = renderAt("/today", 390);
    expect(
      container.querySelector('[data-shell="mobile-fullbleed"]'),
    ).toBeTruthy();
    expect(container.querySelector('[data-od-id="iphone-shell"]')).toBeNull();
  });

  it("five-tab bar mounts with verbatim labels including 差一个", () => {
    const { container } = renderAt("/today", 1024);
    const tabbar = container.querySelector(
      '[data-od-id="tabbar"]',
    ) as HTMLElement | null;
    expect(tabbar).toBeTruthy();
    for (const label of ["今天", "活动", "差一个", "消息", "我"]) {
      expect(within(tabbar!).getByText(label)).toBeTruthy();
    }
    expect(tabbar!.querySelector('[data-tab="create"] img.tab-png-create')).toBeTruthy();
    expect(
      container.querySelector('[data-screen="screen-B1-today"]') ||
        container.querySelector('[data-accessibility-id="screen-B1-today"]'),
    ).toBeTruthy();
  });
});
