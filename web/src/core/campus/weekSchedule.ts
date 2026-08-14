import type { Gathering } from "../api/repositories";

export interface ScheduleBlock {
  id: string;
  title: string;
  start: Date;
  end: Date;
  detail?: string;
  kind: "course" | "gathering";
  href: string;
  changed?: boolean;
}

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

export function startOfWeekMonday(date: Date): Date {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d;
}

export function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

export function weekdayLabel(date: Date): string {
  const day = date.getDay();
  return `周${WEEKDAYS[day === 0 ? 6 : day - 1]}`;
}

export function formatMonthDay(date: Date): string {
  return `${date.getMonth() + 1}/${date.getDate()}`;
}

export function weekRangeLabel(weekStart: Date): string {
  const end = addDays(weekStart, 6);
  return `${formatMonthDay(weekStart)} – ${formatMonthDay(end)}`;
}

function parseInstant(value: unknown): Date | null {
  if (typeof value !== "string" || !value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function gridTitle(value: string): string {
  return value.replace(/^本?\s*[（(][^）)]{1,6}[）)]\s*/, "").trim();
}

export function timeRangeLabel(start: Date, end: Date): string {
  const fmt = (d: Date) =>
    `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return `${fmt(start)}–${fmt(end)}`;
}

export function blocksFromTimetable(
  entries: Array<Record<string, unknown>>,
): ScheduleBlock[] {
  return entries.flatMap((entry, i) => {
    const start = parseInstant(entry.start_at);
    const end = parseInstant(entry.end_at);
    if (!start || !end) return [];
    const courseId = String(entry.course_id ?? entry.id ?? i);
    return [
      {
        id: `c-${courseId}-${start.getTime()}`,
        title: String(entry.course_name ?? entry.name ?? entry.title ?? "课程"),
        start,
        end,
        detail: typeof entry.location === "string" ? entry.location : undefined,
        kind: "course" as const,
        href: `/today/course/${courseId}`,
        changed: entry.changed === true,
      },
    ];
  });
}

const HIDDEN_GATHERING = /draft|dissolved|archived|unknown/i;

export function blocksFromGatherings(
  gatherings: Gathering[],
  weekStart: Date,
): ScheduleBlock[] {
  const weekEnd = addDays(weekStart, 7);
  return gatherings.flatMap((g) => {
    if (HIDDEN_GATHERING.test(g.status ?? "")) return [];
    const start = parseInstant(g.start_at ?? g.starts_at);
    if (!start || start < weekStart || start >= weekEnd) return [];
    const end = parseInstant(g.end_at ?? g.ends_at) ?? new Date(start.getTime() + 3_600_000);
    return [
      {
        id: `g-${g.id}`,
        title: g.title ?? "约局",
        start,
        end,
        detail: g.location ?? g.campus ?? undefined,
        kind: "gathering" as const,
        href: `/gathering/${g.id}`,
      },
    ];
  });
}

export function hourRange(blocks: ScheduleBlock[]): { start: number; end: number } {
  if (blocks.length === 0) return { start: 8, end: 18 };
  let lower = 24;
  let upper = 0;
  for (const block of blocks) {
    lower = Math.min(lower, block.start.getHours());
    const endHour = block.end.getHours();
    const endMinute = block.end.getMinutes();
    upper = Math.max(upper, endMinute > 0 ? endHour + 1 : endHour);
  }
  return { start: Math.max(0, lower), end: Math.min(24, Math.max(upper, lower + 1)) };
}
