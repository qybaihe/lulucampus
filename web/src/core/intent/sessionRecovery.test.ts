/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, beforeEach } from "vitest";
import {
  clearIntentDraft,
  intentDraftScope,
  loadIntentDraft,
  saveIntentDraft,
  type IntentRecoveryDraft,
} from "./sessionRecovery";

const draft: IntentRecoveryDraft = {
  text: "周六晚上珠海校区一起打羽毛球，4人",
  moodNote: "",
  goal: "打球",
  capabilitiesText: "",
  rolesText: "双打",
  campus: "珠海校区",
  intensity: "balanced",
  socialMode: "after_full",
  sameGenderOnly: false,
  minimumSize: 2,
  targetSize: 4,
  startAt: "2026-08-15T19:00",
  endAt: "2026-08-15T21:00",
};

describe("intent session recovery", () => {
  beforeEach(() => {
    clearIntentDraft("default");
    clearIntentDraft(intentDraftScope("c1"));
  });

  it("round-trips a draft in localStorage", () => {
    saveIntentDraft("default", draft);
    expect(loadIntentDraft("default")?.text).toBe(draft.text);
  });

  it("scopes competition drafts separately", () => {
    saveIntentDraft(intentDraftScope("c1"), { ...draft, text: "数模" });
    expect(loadIntentDraft("default")).toBeNull();
    expect(loadIntentDraft(intentDraftScope("c1"))?.text).toBe("数模");
  });
});
