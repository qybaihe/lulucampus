import { describe, expect, it } from "vitest";
import {
  isSessionExpiredError,
  parseEnvelope,
} from "./envelope";

describe("parseEnvelope", () => {
  it("parses successful data/meta envelope", () => {
    const result = parseEnvelope<{ id: string }>({
      data: { id: "c1" },
      meta: { request_id: "r1" },
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.id).toBe("c1");
      expect(result.meta.request_id).toBe("r1");
    }
  });

  it("parses error envelope without inventing success", () => {
    const result = parseEnvelope({
      error: {
        code: "NOT_FOUND",
        message: "不存在",
        details: {},
        request_id: "abc",
      },
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("NOT_FOUND");
      expect(result.error.message).toBe("不存在");
      expect(result.error.request_id).toBe("abc");
    }
  });

  it("rejects missing data field", () => {
    const result = parseEnvelope({ meta: {} });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.code).toBe("INVALID_ENVELOPE");
    }
  });

  it("rejects null body", () => {
    const result = parseEnvelope(null);
    expect(result.ok).toBe(false);
  });
});

describe("isSessionExpiredError", () => {
  it("treats HTTP 401 as session expired", () => {
    expect(
      isSessionExpiredError({ code: "X", message: "x" }, 401),
    ).toBe(true);
  });

  it("treats known auth codes as session expired", () => {
    expect(
      isSessionExpiredError({
        code: "SESSION_EXPIRED",
        message: "gone",
      }),
    ).toBe(true);
  });
});
