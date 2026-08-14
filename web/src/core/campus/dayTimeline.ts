/** 今日日程时间轴：对齐 iOS TodayTimelineRow（过去 / 进行中 / 即将）。 */

export type TimelinePhase = "past" | "current" | "upcoming";

export type TimelineItem = {
  id?: string;
  title?: string;
  subtitle?: string;
  time_label?: string | null;
  location?: string | null;
  gathering_id?: string | null;
  course_id?: string | null;
  kind?: string;
  start_at?: string | null;
  end_at?: string | null;
  starts_at?: string;
};

export function formatClock(value?: string | null): string {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function timelineRange(item: TimelineItem): string {
  if (item.time_label && String(item.time_label).trim()) return String(item.time_label);
  const start = formatClock(item.start_at ?? item.starts_at ?? null);
  const end = formatClock(item.end_at ?? null);
  if (start && end) return `${start}–${end}`;
  return start;
}

export function splitTimeRange(range: string): [string, string] {
  if (!range) return ["", ""];
  const parts = range.split(/[–-]/);
  if (parts.length >= 2) return [parts[0]!.trim(), parts[1]!.trim()];
  return [range.trim(), ""];
}

export function timelinePhase(
  item: TimelineItem,
  now: number = Date.now(),
): TimelinePhase {
  const startRaw = item.start_at ?? item.starts_at ?? null;
  if (!startRaw) return "upcoming";
  const start = new Date(startRaw).getTime();
  if (Number.isNaN(start)) return "upcoming";
  if (item.end_at) {
    const end = new Date(item.end_at).getTime();
    if (!Number.isNaN(end)) {
      if (now > end) return "past";
      return now >= start ? "current" : "upcoming";
    }
  }
  return now >= start ? "past" : "upcoming";
}

export function timelineKindLabel(kind?: string): string {
  switch (kind) {
    case "gathering":
      return "活动";
    case "assignment":
      return "作业";
    case "course":
      return "课程";
    default:
      return "日程";
  }
}

export function timelineDetail(item: TimelineItem): string {
  const fromFields = [item.subtitle, item.location]
    .map((value) => (value ? String(value).trim() : ""))
    .filter(Boolean);
  return fromFields[0] ?? timelineKindLabel(item.kind);
}

export function timelineHref(item: TimelineItem): string {
  if (item.gathering_id) return `/gathering/${item.gathering_id}`;
  if (item.kind === "assignment") return "/today/assignments";
  return "/today/timetable";
}
