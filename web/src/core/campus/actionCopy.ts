export interface ActionCopyFact {
  label: string;
  value: string;
}

export interface ActionCopy {
  title: string;
  headline: string;
  timeLine: string | null;
  sticker: string;
  statusLabel: string;
  facts: ActionCopyFact[];
  note: string | null;
}

type Json = unknown;

const HIDDEN_KEYS = new Set([
  "source",
  "snapshot_hash",
  "hash",
  "idempotency_key",
  "tool_trace",
  "action",
  "action_name",
  "commit_action_name",
  "params",
  "preview_snapshot",
  "user_id",
  "gathering_id",
  "status",
  "ok",
  "confirm_required",
  "seminar_id",
  "include_full",
  "days",
]);

const TECHNICAL_TOKEN = /^[a-z][a-z0-9]*([._][a-z0-9]+)+$/;

export function makeCampusActionCopy(input: {
  action_name?: string | null;
  status?: string | null;
  params?: Record<string, Json> | null;
  preview_snapshot?: Record<string, Json> | null;
}): ActionCopy {
  const actionName = input.action_name ?? "";
  const fields = mergedFields(input.params ?? {}, input.preview_snapshot ?? {});
  const venueType = fields.venue_type;
  const kind = fields.kind;
  const venue = fields.venue;
  const room = fields.room;
  const date = fields.date ? formatDate(fields.date) : undefined;
  const start = fields.start;
  const end = fields.end;
  const timeRange = start && end ? `${start} – ${end}` : start ?? end;
  const timeLine = [date, timeRange].filter(Boolean).join(" · ") || null;

  const title = titleFor(actionName, venueType, kind);
  let headlineParts: string[];
  if (actionName.startsWith("gym.")) {
    headlineParts = [venue, venueType].filter(Boolean) as string[];
  } else if (actionName.startsWith("room.")) {
    headlineParts = [kind, room].filter(Boolean) as string[];
  } else if (actionName.startsWith("seminar.")) {
    headlineParts = [fields.title, fields.department].filter(Boolean) as string[];
  } else {
    headlineParts = [venue, room, kind, venueType].filter(Boolean) as string[];
  }

  const facts: ActionCopyFact[] = [];
  const add = (label: string, value?: string) => {
    if (!value) return;
    if (facts.some((fact) => fact.label === label)) return;
    facts.push({ label, value });
  };
  add("项目", venueType);
  add("类型", kind);
  add("地点", venue);
  add("房间", room);
  add("区域", fields.lab);
  add("日期", date);
  add("时段", timeRange);
  add("出发", fields.from ?? fields.board);
  add("到达", fields.to ?? fields.arrive);
  add("用途", fields.title);
  add("备注", fields.memo);
  add("同行", fields.members);
  add("配套", fields.services);
  add("地点", fields.location);
  add("人数", fields.count ?? fields.people);
  add("关键词", fields.query);

  const isReference =
    input.preview_snapshot?.source === "peer_overlap_template";

  return {
    title,
    headline: headlineParts.length ? headlineParts.join(" · ") : title,
    timeLine,
    sticker: stickerFor(actionName, venueType),
    statusLabel: isReference ? "时段参考" : statusLabelFor(input.status ?? ""),
    facts,
    note: fields.message ?? fields.summary ?? null,
  };
}

export function authorizationLine(authorized: number, required: number): string {
  if (required <= 0) return "";
  if (required === 1) {
    return authorized >= 1 ? "这一步已经核对过了" : "提交前再确认一遍";
  }
  if (authorized >= required) return "大家都核对过了";
  return `${authorized} / ${required} 位已核对`;
}

function mergedFields(
  params: Record<string, Json>,
  snapshot: Record<string, Json>,
): Record<string, string> {
  const combined = { ...unwrap(snapshot), ...unwrap(params) };
  const fields: Record<string, string> = {};
  for (const [key, value] of Object.entries(combined)) {
    const leaf = key.split(".").at(-1) ?? key;
    if (HIDDEN_KEYS.has(leaf) || HIDDEN_KEYS.has(key)) continue;
    const text = displayValue(value);
    if (text) fields[leaf] = text;
  }
  return fields;
}

function unwrap(dict: Record<string, Json>): Record<string, Json> {
  const result = { ...dict };
  const nested = result.params;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    Object.assign(result, nested as Record<string, Json>);
    delete result.params;
  }
  return result;
}

function displayValue(value: Json): string | undefined {
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed || TECHNICAL_TOKEN.test(trimmed)) return undefined;
    return trimmed;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return Number.isInteger(value) ? String(value) : String(value);
  }
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value)) {
    const parts = value.map(displayValue).filter((item): item is string => Boolean(item));
    return parts.length ? parts.join("、") : undefined;
  }
  return undefined;
}

function titleFor(actionName: string, venueType?: string, kind?: string): string {
  if (actionName.startsWith("gym.")) {
    return venueType ? `预约${venueType}` : "预约场馆";
  }
  if (actionName.startsWith("room.")) return "预约研讨室";
  if (actionName.startsWith("seminar.")) return "预约讲座";
  if (actionName.startsWith("transit.qiguan")) return "岐关预约";
  if (actionName.startsWith("transit.")) return "校园班车";
  if (actionName.startsWith("timetable.")) return "课表";
  if (actionName.startsWith("assignment.")) return "作业";
  if (actionName.startsWith("career.")) return "招聘活动";
  if (kind) return kind;
  return "校园行动";
}

function stickerFor(actionName: string, venueType?: string): string {
  if (venueType === "篮球") return "basketball.png";
  if (venueType === "羽毛球") return "badminton.png";
  if (actionName.startsWith("gym.")) return "running-shoe.png";
  if (actionName.startsWith("room.") || actionName.startsWith("seminar.")) {
    return "seminar-room-sign.png";
  }
  if (actionName.startsWith("transit.")) return "school-bus.png";
  if (actionName.startsWith("timetable.") || actionName.startsWith("assignment.")) {
    return "desk-calendar.png";
  }
  return "approval-stamp.png";
}

function statusLabelFor(status: string): string {
  if (status === "succeeded") return "已完成";
  if (status === "failed") return "未完成";
  if (status === "previewed") return "待核对";
  return "进行中";
}

function formatDate(raw: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  const date = new Date(`${raw}T12:00:00+08:00`);
  const weekday = new Intl.DateTimeFormat("zh-CN", {
    weekday: "long",
    timeZone: "Asia/Shanghai",
  }).format(date);
  const [, month, day] = raw.split("-");
  return `${Number(month)}月${Number(day)}日 ${weekday}`;
}
