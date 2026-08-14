/** 赛事卡视觉：对齐 iOS CompetitionsView sticker / 标题阶梯 / 截止紧迫标。 */

export function competitionSticker(item: {
  name?: string;
  tracks?: string[];
}): string {
  const haystack = `${item.name ?? ""} ${(item.tracks ?? []).join(" ")}`.toLowerCase();
  if (/科研|研究|论文|学术|实验/.test(haystack)) return "flask.png";
  if (/创业|创新|商业|点子|创投/.test(haystack)) return "bulb.png";
  return "trophy.png";
}

export function competitionTitleClass(name: string): string {
  if (name.length < 13) return "t-t3";
  if (name.length < 22) return "t-call";
  return "t-foot";
}

export type DeadlineBadge = { kind: "gap" | "quiet"; label: string };

export function deadlineBadge(
  iso: string,
  now = Date.now(),
): DeadlineBadge | null {
  const deadline = new Date(iso);
  if (Number.isNaN(deadline.getTime())) return null;
  const startOfDay = (t: number) => {
    const d = new Date(t);
    d.setHours(0, 0, 0, 0);
    return d.getTime();
  };
  const daysLeft = Math.max(
    0,
    Math.round((startOfDay(deadline.getTime()) - startOfDay(now)) / 86_400_000),
  );
  if (daysLeft <= 3) {
    return {
      kind: "gap",
      label: daysLeft === 0 ? "今天截止" : `还剩 ${daysLeft} 天截止`,
    };
  }
  return {
    kind: "quiet",
    label: `截止 ${deadline.getMonth() + 1}月${deadline.getDate()}日 · 还剩 ${daysLeft} 天`,
  };
}
