/** 对齐 iOS SessionRecoveryStore：刷新/离开前把意图草稿留在本机。 */

export interface IntentRecoveryDraft {
  text: string;
  moodNote: string;
  goal: string;
  capabilitiesText: string;
  rolesText: string;
  campus: string;
  intensity: string;
  socialMode: string;
  sameGenderOnly: boolean;
  minimumSize: number;
  targetSize: number;
  startAt: string;
  endAt: string;
  cardID?: string;
  competitionID?: string | null;
}

const PREFIX = "onemore.intent-draft.";

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function intentDraftScope(competitionID?: string | null): string {
  return competitionID?.trim() ? `competition:${competitionID}` : "default";
}

export function saveIntentDraft(scope: string, draft: IntentRecoveryDraft): void {
  const store = storage();
  if (!store) return;
  store.setItem(`${PREFIX}${scope}`, JSON.stringify(draft));
}

export function loadIntentDraft(scope: string): IntentRecoveryDraft | null {
  const store = storage();
  if (!store) return null;
  const raw = store.getItem(`${PREFIX}${scope}`);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as IntentRecoveryDraft;
    if (!parsed || typeof parsed.text !== "string") return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearIntentDraft(scope: string): void {
  storage()?.removeItem(`${PREFIX}${scope}`);
}
