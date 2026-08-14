/** 校园活动列表字段归一（对齐 iOS CampusEvent.displayType）。 */

export function campusEventDisplayType(type?: string | null): string {
  switch (type) {
    case "teachin":
    case "宣讲会":
      return "宣讲";
    case "seminar":
    case "lecture":
      return "讲座";
    case "club":
    case "society":
      return "社团";
    case "recruitment":
      return "招新";
    case "career_fair":
    case "招聘会":
      return "招聘";
    case "performance":
      return "演出";
    default:
      return type?.trim() || "活动";
  }
}

export function campusEventTime(item: Record<string, unknown>): string {
  const raw = item.starts_at ?? item.start_at ?? item.startsAt ?? item.startAt;
  if (typeof raw !== "string" || !raw) return "时间待官方确认";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return "时间待官方确认";
  return date.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function campusEventLocation(item: Record<string, unknown>): string {
  const loc = item.location ?? item.place ?? item.venue;
  return typeof loc === "string" && loc.trim() ? loc : "地点待官方确认";
}
