import { capabilityLabel, type CompetitionTeam } from "../api/repositories";

export function teamFilled(team: CompetitionTeam): number {
  return Math.min(team.member_count ?? 0, team.target_size ?? 0);
}

export function teamMissingCount(team: CompetitionTeam): number {
  if (typeof team.missing_count === "number" && team.missing_count >= 0) {
    return team.missing_count;
  }
  return Math.max(0, (team.target_size ?? 0) - (team.member_count ?? 0));
}

export function teamMissingRoles(team: CompetitionTeam): string[] {
  const roles = team.missing_roles ?? team.required_roles ?? [];
  return roles.filter(Boolean);
}

/** 角色缺口文案（对齐 iOS CompetitionTeam.gapDescription）：「差一个算法」。 */
export function gapDescription(team: CompetitionTeam): string | null {
  const labels = teamMissingRoles(team).map(capabilityLabel);
  if (labels.length === 1) return `差一个${labels[0]}`;
  if (labels.length > 1) return `还差 ${labels.length} 个角色：${labels.join("、")}`;
  const missing = teamMissingCount(team);
  if (missing > 0) return `还差 ${missing} 人`;
  return null;
}

export function recruitingHeadline(count: number | null): string {
  if (count == null) return "正在招人的队伍";
  if (count === 0) return "暂时还没有队伍在招人";
  return `有 ${count} 支队伍正在招人`;
}
