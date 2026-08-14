/** 今天首页校园工具格。与 iOS TodayView 四格一致：日程 / 活动 / 班车 / 我的局。 */
export const CAMPUS_HOME_TOOLS = [
  { sticker: "desk-calendar.png", label: "日程", to: "/today/timetable", id: "today-timetable" },
  { sticker: "poster-blank.png", label: "活动", to: "/today/events", id: "today-events" },
  { sticker: "school-bus.png", label: "班车", to: "/today/transit", id: "today-transit" },
  { sticker: "chair-empty.png", label: "我的局", to: "/gatherings/mine", id: "today-my-gatherings" },
] as const;
