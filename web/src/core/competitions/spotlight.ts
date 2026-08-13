/**
 * Client-side spotlight for competition cards.
 * Server already scores taste_fit; the client decides the "很适合你 + 正好差一个"
 * jackpot, reorders the list, and owns the marquee ring.
 */

export interface SpotlightCompetition {
  id?: string;
  taste_fit?: number | null;
  taste_fit_label?: string | null;
  recruit_gap_count?: number | null;
  recruit_gap_labels?: string[];
  recruit_hints?: string[];
}

export interface SpotlightTeam {
  member_count?: number;
  target_size?: number;
}

const ONE_ROLE_HINT = /再找会(.+)的人/;
/** Close enough that the client can promote the card into the jackpot ring. */
const HOT_FIT = 0.5;

export function recruitGapCount(item: SpotlightCompetition): number {
  if (typeof item.recruit_gap_count === "number" && item.recruit_gap_count >= 0) {
    return item.recruit_gap_count;
  }
  for (const hint of item.recruit_hints ?? []) {
    if (ONE_ROLE_HINT.test(hint)) return 1;
    const multi = hint.match(/补上：(.+)/);
    if (multi?.[1]) return multi[1].split("、").filter(Boolean).length;
  }
  return 0;
}

export function recruitGapLabel(item: SpotlightCompetition): string | null {
  const labels = item.recruit_gap_labels ?? [];
  if (recruitGapCount(item) === 1 && labels[0]) return labels[0];
  for (const hint of item.recruit_hints ?? []) {
    const match = hint.match(ONE_ROLE_HINT);
    if (match?.[1]) return match[1];
  }
  return null;
}

export function isHotSeat(item: SpotlightCompetition): boolean {
  if (recruitGapCount(item) !== 1) return false;
  if (item.taste_fit_label === "很适合你") return true;
  return (item.taste_fit ?? 0) >= HOT_FIT;
}

/** Jackpot cards present as 很适合你 even if the server said 和你有点像. */
export function spotlightFitLabel(item: SpotlightCompetition): string | null {
  if (isHotSeat(item)) return "很适合你";
  return item.taste_fit_label ?? null;
}

export function hotSeatChip(item: SpotlightCompetition): string | null {
  if (!isHotSeat(item)) return null;
  const label = recruitGapLabel(item);
  return label ? `正好差一个${label}` : "正好差一个";
}

export function isOneSeatLeft(team: SpotlightTeam): boolean {
  const target = team.target_size ?? 0;
  const filled = team.member_count ?? 0;
  return target > 0 && target - filled === 1;
}

export function isHotTeam(item: SpotlightCompetition, team: SpotlightTeam): boolean {
  return isHotSeat(item) && isOneSeatLeft(team);
}

function rankScore(item: SpotlightCompetition): number {
  if (isHotSeat(item)) return 3;
  if (item.taste_fit_label === "很适合你" || (item.taste_fit ?? 0) >= HOT_FIT) return 2;
  if (item.taste_fit_label === "和你有点像") return 1;
  return 0;
}

/** Stable client reorder: jackpot first, then strong fit, then 和你有点像. */
export function rankCompetitionsForYou<T extends SpotlightCompetition>(items: T[]): T[] {
  return items
    .map((item, index) => ({ item, index, rank: rankScore(item) }))
    .sort((a, b) => b.rank - a.rank || a.index - b.index)
    .map((row) => row.item);
}
