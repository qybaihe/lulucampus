export const NOTIFICATION_CATEGORY_LABELS: Record<string, string> = {
  gathering_updates: "成局",
  schedule_reminders: "日程",
  chat_messages: "消息",
  action_updates: "行动",
  trust_updates: "信任",
  competition_deadlines: "赛事",
};

const SCREEN_PATHS: Record<string, string> = {
  B3: "/today/timetable",
  B4: "/today/assignments",
  B5: "/today/gym",
  B6: "/today/room",
  B7: "/today/events",
  M3: "/me/trust",
  E15: "/relations",
};

function firstString(
  ...values: unknown[]
): string | undefined {
  for (const value of values) {
    if (typeof value === "string" && value.length > 0) return value;
  }
  return undefined;
}

export function categoryLabel(category?: string | null): string {
  if (!category) return "提醒";
  return NOTIFICATION_CATEGORY_LABELS[category] ?? "提醒";
}

export function notificationSummary(
  payload?: Record<string, unknown> | null,
  title?: string | null,
): string {
  const summary = payload?.summary;
  if (typeof summary === "string" && summary.trim()) return summary;
  if (typeof title === "string" && title.trim()) return title;
  return "你有一条新提醒";
}

export function relativeTimeLabel(iso: string, now = Date.now()): string {
  const stamp = new Date(iso).getTime();
  if (Number.isNaN(stamp)) return "";
  const deltaSeconds = Math.round((stamp - now) / 1000);
  const abs = Math.abs(deltaSeconds);
  const rtf = new Intl.RelativeTimeFormat("zh-CN", { numeric: "auto" });
  if (abs < 60) return rtf.format(deltaSeconds, "second");
  if (abs < 3600) return rtf.format(Math.round(deltaSeconds / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(deltaSeconds / 3600), "hour");
  return rtf.format(Math.round(deltaSeconds / 86400), "day");
}

export function pathFromNotification(item: {
  payload?: Record<string, unknown> | null;
  type?: string;
}): string | null {
  const payload = item.payload ?? {};
  const deepLink = firstString(payload.deep_link, payload.url);
  if (deepLink) {
    const mapped = pathFromDeepLink(deepLink, payload);
    if (mapped) return mapped;
  }
  const gatheringId = firstString(payload.gathering_id);
  if (gatheringId) return `/gathering/${gatheringId}`;
  const channelId = firstString(payload.channel_id);
  if (channelId) return `/channel/${channelId}`;
  const relationId = firstString(payload.relation_id);
  if (relationId) return `/relation/${relationId}`;
  const competitionId = firstString(payload.competition_id);
  if (competitionId) return `/competition/${competitionId}`;
  const screenId = firstString(payload.screen_id);
  if (screenId) return SCREEN_PATHS[screenId.toUpperCase()] ?? null;
  return null;
}

export function pathFromDeepLink(
  raw: string,
  payload: Record<string, unknown> = {},
): string | null {
  if (!raw.startsWith("onemore://")) {
    if (raw.startsWith("/")) return raw;
    return null;
  }
  const rest = raw.slice("onemore://".length);
  const [head, ...parts] = rest.split("/").filter(Boolean);
  switch (head) {
    case "gathering":
      return parts[0] ? `/gathering/${parts[0]}` : "/gatherings/mine";
    case "channel":
      return parts[0] ? `/channel/${parts[0]}` : "/messages";
    case "relation":
      return parts[0] ? `/relation/${parts[0]}` : "/relations";
    case "goal":
      return parts[0] ? `/goal/${parts[0]}` : "/relations";
    case "competition":
      return parts[0] ? `/competition/${parts[0]}` : "/competitions";
    case "screen": {
      const id = (parts[0] ?? "").toUpperCase();
      if (id === "E16") {
        const relationId = firstString(payload.relation_id);
        return relationId ? `/relation/${relationId}` : "/relations";
      }
      if (id === "E14") {
        const channelId = firstString(payload.channel_id);
        return channelId ? `/channel/${channelId}` : "/messages";
      }
      if (id === "E3" || id === "E5" || id === "E6" || id === "E7") {
        const gatheringId = firstString(payload.gathering_id);
        return gatheringId ? `/gathering/${gatheringId}` : "/gatherings/mine";
      }
      return SCREEN_PATHS[id] ?? "/today";
    }
    case "auth":
      return "/auth";
    case "relations":
      return "/relations";
    case "trust":
      return "/me/trust";
    default:
      return null;
  }
}

export function categoryEnabled(
  categories: Record<string, boolean | undefined> | undefined,
  category: string | undefined,
): boolean {
  const key = category && category.length > 0 ? category : "gathering_updates";
  return categories?.[key] !== false;
}
