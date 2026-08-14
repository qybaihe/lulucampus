import { APIClientError } from "../api/client";

export type TrustRecoveryKind = "gathering" | "share";

export interface TrustRequirementContext {
  requiredLevel: string;
  capability?: string;
  serverMessage: string;
  recoveryKind: TrustRecoveryKind;
  recoveryId: string;
}

const CAPABILITY_TITLES: Record<string, string> = {
  competition_pool: "比赛组队",
  duo_gathering: "双人高承诺局",
  cross_college_matching: "跨院系匹配",
  large_group: "大型多人局",
  backfill_fast_lane: "补位快速通道",
  initiate_gathering: "直接发起",
  recurring_gathering: "固定周期局",
};

export function trustCapabilityTitle(capability?: string | null): string {
  if (!capability) return "当前局准入";
  return CAPABILITY_TITLES[capability] ?? capability;
}

export function trustRecoveryTitle(kind: TrustRecoveryKind): string {
  return kind === "share" ? "继续响应原缺口卡" : "继续加入原来的局";
}

export function trustLevelRank(value: string): number {
  const n = Number(value.replace(/^T/i, ""));
  return Number.isFinite(n) ? n : -1;
}

export function parseTrustRequirement(
  error: unknown,
  recovery: { kind: TrustRecoveryKind; id: string },
): TrustRequirementContext | null {
  if (!(error instanceof APIClientError) || error.body?.code !== "TRUST_LEVEL_REQUIRED") {
    return null;
  }
  const details = error.body.details ?? {};
  const requiredLevel =
    typeof details.required_level === "string" ? details.required_level : "";
  if (!requiredLevel) return null;
  const capability =
    typeof details.capability === "string" ? details.capability : undefined;
  return {
    requiredLevel,
    capability,
    serverMessage: error.body.message || error.message,
    recoveryKind: recovery.kind,
    recoveryId: recovery.id,
  };
}

export function isTrustRequirementContext(
  value: unknown,
): value is TrustRequirementContext {
  if (!value || typeof value !== "object") return false;
  const row = value as Record<string, unknown>;
  return (
    typeof row.requiredLevel === "string" &&
    typeof row.serverMessage === "string" &&
    (row.recoveryKind === "gathering" || row.recoveryKind === "share") &&
    typeof row.recoveryId === "string"
  );
}
