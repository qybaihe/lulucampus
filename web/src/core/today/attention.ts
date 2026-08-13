export interface AttentionItem {
  id: string;
  title: string;
  badge?: string;
  deepLink: string;
}

function asString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function titleFor(raw: Record<string, unknown>): string {
  if (asString(raw.type) === "confirmation") {
    const name = asString(raw.from_name);
    return name ? `${name} 有一个局等待你确认` : "有一个局等待你确认";
  }
  const title = asString(raw.title);
  return title ? `「${title}」等待核对` : "有一份行动预览等待核对";
}

/** 今天接口 pending → 消息页待办；同一局里的预览和行动只留一条。 */
export function attentionItems(
  pending: Array<Record<string, unknown>> | undefined | null,
): AttentionItem[] {
  const seen = new Set<string>();
  const items: AttentionItem[] = [];
  for (const raw of pending ?? []) {
    const gatheringId = asString(raw.gathering_id);
    const actionId = asString(raw.action_id);
    const deepLink = asString(raw.deep_link);
    const id = gatheringId ?? actionId ?? deepLink;
    if (!id || !deepLink || seen.has(id)) continue;
    seen.add(id);
    items.push({
      id,
      title: titleFor(raw),
      badge: asString(raw.type) === "confirmation" ? "差你 1 票" : undefined,
      deepLink,
    });
  }
  return items;
}

export function pathFromAttentionLink(deepLink: string): string | null {
  if (deepLink.startsWith("/")) return deepLink;
  if (!deepLink.startsWith("onemore://")) return null;
  const rest = deepLink.slice("onemore://".length);
  const [head, ...parts] = rest.split("/").filter(Boolean);
  if (head === "gathering" && parts[0]) return `/gathering/${parts[0]}`;
  if (head === "action" && parts[0]) return `/today/action-preview?action=${parts[0]}`;
  return null;
}
