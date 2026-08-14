/** 今天页场景触发：对齐后端 `_scene_trigger` 与 iOS TodayView 字段。 */

export type SceneTriggerView = {
  key: string;
  title: string;
  body: string;
  cta_label?: string;
};

/**
 * 后端返回 scene_key / text / context.title；
 * 旧客户端与部分测试用 key / title / body。两边都认。
 */
export function normalizeSceneTrigger(raw: unknown): SceneTriggerView | null {
  if (!raw || typeof raw !== "object") return null;
  const o = raw as Record<string, unknown>;
  const key =
    (typeof o.scene_key === "string" && o.scene_key) ||
    (typeof o.key === "string" && o.key) ||
    "";
  if (!key) return null;
  const context =
    o.context && typeof o.context === "object"
      ? (o.context as Record<string, unknown>)
      : undefined;
  const contextTitle =
    typeof context?.title === "string" ? context.title.trim() : "";
  const title =
    (typeof o.title === "string" && o.title.trim()) ||
    contextTitle ||
    "现在有个合适的空档";
  const body =
    (typeof o.text === "string" && o.text) ||
    (typeof o.body === "string" && o.body) ||
    "";
  const cta_label =
    typeof o.cta_label === "string" && o.cta_label ? o.cta_label : undefined;
  return { key, title, body, cta_label };
}
