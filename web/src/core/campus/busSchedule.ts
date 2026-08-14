/**
 * B9 班车离线时刻表。对齐 iOS CampusBusSchedule.swift。
 * 数据来源：sysu-anything bus-schedule.json（2026-08-12 快照）与岐关车班次。
 */

export type BusDayKind = "工作日" | "节假日";

export interface BusDeparture {
  time: string;
  via?: string;
  staffOnly: boolean;
  arrive?: string;
  express: boolean;
}

export interface BusRoute {
  id: string;
  from: string;
  to: string;
  fromStation: string;
  toStation: string;
  isQiguan: boolean;
  workday: BusDeparture[];
  holiday: BusDeparture[];
}

export const BUS_CAMPUSES = ["东校园", "南校园", "北校园", "珠海校区"] as const;

function shuttle(
  time: string,
  via?: string,
  staffOnly = false,
): BusDeparture {
  return { time, via, staffOnly, express: false };
}

function qiguan(board: string, arrive: string, express: boolean): BusDeparture {
  return { time: board, arrive, staffOnly: false, express };
}

export const BUS_ROUTES: BusRoute[] = [
  {
    id: "gz-east-north",
    from: "东校园",
    to: "北校园",
    fromStation: "兰园 3 号（原生科院大楼）",
    toStation: "北校园南门车房楼下",
    isQiguan: false,
    workday: [
      shuttle("7:00", "途经黄埔大道", true),
      shuttle("8:00", "途经黄埔大道"),
      shuttle("10:00", "途经黄埔大道"),
      shuttle("12:10", "途经黄埔大道"),
      shuttle("15:30", "途经黄埔大道"),
      shuttle("16:20", "途经黄埔大道"),
      shuttle("17:10", "途经黄埔大道", true),
      shuttle("18:30", "途经黄埔大道", true),
      shuttle("21:00", "途经黄埔大道"),
      shuttle("21:55", "途经黄埔大道"),
    ],
    holiday: [
      shuttle("9:30", "途经黄埔大道"),
      shuttle("13:30", "途经黄埔大道"),
    ],
  },
  {
    id: "gz-north-east",
    from: "北校园",
    to: "东校园",
    fromStation: "北校园南门车房楼下",
    toStation: "兰园 3 号（原生科院大楼）",
    isQiguan: false,
    workday: [
      shuttle("7:00", "途经黄埔大道", true),
      shuttle("7:50", "途经黄埔大道", true),
      shuttle("8:10", "途经黄埔大道", true),
      shuttle("9:00", "途经黄埔大道"),
      shuttle("9:40", "途经黄埔大道"),
      shuttle("13:10", "途经黄埔大道"),
      shuttle("15:10", "途经黄埔大道"),
      shuttle("17:45", "途经黄埔大道", true),
      shuttle("18:50", "途经黄埔大道"),
      shuttle("20:50", "途经黄埔大道"),
    ],
    holiday: [
      shuttle("8:20", "途经黄埔大道"),
      shuttle("12:40", "途经黄埔大道"),
    ],
  },
  {
    id: "gz-east-south",
    from: "东校园",
    to: "南校园",
    fromStation: "兰园 3 号（原生科院大楼）",
    toStation: "南校园南门停车场",
    isQiguan: false,
    workday: [
      shuttle("7:10", "校园内经教师公寓对面", true),
      shuttle("8:00", "校园内经教师公寓对面", true),
      shuttle("10:00", "中途 1 车停坚真花园"),
      shuttle("12:10", "中途 1 车停坚真花园"),
      shuttle("13:20", "校园内经教师公寓对面"),
      shuttle("13:50", "校园内经教师公寓对面"),
      shuttle("15:30", "校园内经教师公寓对面"),
      shuttle("16:20", "校园内经教师公寓对面"),
      shuttle("17:10", "中途 1 车停坚真花园"),
      shuttle("18:30", "中途 1 车停坚真花园", true),
      shuttle("20:00", "校园内经教师公寓对面"),
      shuttle("21:00", "校园内经教师公寓对面"),
      shuttle("21:55", "校园内经教师公寓对面", true),
      shuttle("22:15", "校园内经教师公寓对面"),
    ],
    holiday: [
      shuttle("9:30", "校园内经教师公寓对面"),
      shuttle("13:30", "校园内经教师公寓对面"),
    ],
  },
  {
    id: "gz-south-east",
    from: "南校园",
    to: "东校园",
    fromStation: "南校园南门停车场",
    toStation: "兰园 3 号（原生科院大楼）",
    isQiguan: false,
    workday: [
      shuttle("7:10", "中途 1 车停坚真花园", true),
      shuttle("8:00", "中途不停"),
      shuttle("8:20", "中途 1 车停坚真花园"),
      shuttle("9:10", "中途 1 车停坚真花园"),
      shuttle("9:50", "中途不停"),
      shuttle("11:00", "中途不停"),
      shuttle("13:20", "中途 1 车停坚真花园"),
      shuttle("15:20", "中途 1 车停坚真花园"),
      shuttle("17:45", "中途不停", true),
      shuttle("18:00", "中途停坚真花园", true),
      shuttle("19:00", "中途不停"),
      shuttle("21:00", "中途不停"),
      shuttle("21:50", "中途不停"),
    ],
    holiday: [shuttle("8:20", "中途不停"), shuttle("12:40", "中途不停")],
  },
  {
    id: "gz-north-south",
    from: "北校园",
    to: "南校园",
    fromStation: "北校园南门车房楼下",
    toStation: "南校园南门停车场",
    isQiguan: false,
    workday: [
      shuttle("7:30", "途经东川路、海印桥", true),
      shuttle("9:00", "中途不停", true),
      shuttle("10:00", "中途不停", true),
      shuttle("12:10", "途经东川路、海印桥", true),
      shuttle("14:10", "途经东川路、海印桥", true),
      shuttle("15:30", "中途不停", true),
      shuttle("17:45", "途经东川路、海印桥", true),
    ],
    holiday: [],
  },
  {
    id: "gz-south-north",
    from: "南校园",
    to: "北校园",
    fromStation: "南校园南门停车场",
    toStation: "北校园南门车房楼下",
    isQiguan: false,
    workday: [
      shuttle("7:30", "途经怡乐路口、海印桥", true),
      shuttle("9:30", "中途不停", true),
      shuttle("10:30", "中途不停", true),
      shuttle("12:10", "途经怡乐路口、海印桥", true),
      shuttle("14:10", "途经怡乐路口、海印桥", true),
      shuttle("16:15", "中途不停", true),
      shuttle("17:45", "途经怡乐路口、海印桥", true),
    ],
    holiday: [],
  },
  {
    id: "qg-south-zhuhai",
    from: "南校园",
    to: "珠海校区",
    fromStation: "南校园岐关服务部",
    toStation: "珠海中大岐关服务点",
    isQiguan: true,
    workday: [
      qiguan("9:00", "10:40", true),
      qiguan("12:00", "13:40", false),
      qiguan("15:00", "16:40", true),
      qiguan("17:30", "19:10", false),
      qiguan("19:00", "20:40", true),
    ],
    holiday: [
      qiguan("9:00", "10:40", true),
      qiguan("12:00", "13:40", false),
      qiguan("15:00", "16:40", true),
      qiguan("17:30", "19:10", false),
      qiguan("19:00", "20:40", true),
    ],
  },
  {
    id: "qg-zhuhai-south",
    from: "珠海校区",
    to: "南校园",
    fromStation: "珠海中大岐关服务点",
    toStation: "南校园岐关服务部",
    isQiguan: true,
    workday: [
      qiguan("8:15", "9:55", false),
      qiguan("12:00", "13:40", true),
      qiguan("14:30", "16:10", false),
      qiguan("16:30", "18:10", true),
      qiguan("17:30", "19:10", true),
    ],
    holiday: [
      qiguan("8:15", "9:55", false),
      qiguan("12:00", "13:40", true),
      qiguan("14:30", "16:10", false),
      qiguan("16:30", "18:10", true),
      qiguan("17:30", "19:10", true),
    ],
  },
  {
    id: "qg-east-zhuhai",
    from: "东校园",
    to: "珠海校区",
    fromStation: "东校园（大学城）岐关服务部",
    toStation: "珠海中大岐关服务点",
    isQiguan: true,
    workday: [
      qiguan("12:30", "13:40", false),
      qiguan("18:00", "19:10", false),
    ],
    holiday: [
      qiguan("12:30", "13:40", false),
      qiguan("18:00", "19:10", false),
    ],
  },
  {
    id: "qg-zhuhai-east",
    from: "珠海校区",
    to: "东校园",
    fromStation: "珠海中大岐关服务点",
    toStation: "东校园（大学城）岐关服务部",
    isQiguan: true,
    workday: [
      qiguan("8:15", "9:35", false),
      qiguan("14:30", "15:50", false),
    ],
    holiday: [
      qiguan("8:15", "9:35", false),
      qiguan("14:30", "15:50", false),
    ],
  },
];

export function busDepartures(route: BusRoute, kind: BusDayKind): BusDeparture[] {
  return kind === "工作日" ? route.workday : route.holiday;
}

export function busDayKind(date: Date = new Date()): BusDayKind {
  const weekday = date.getDay();
  return weekday === 0 || weekday === 6 ? "节假日" : "工作日";
}

export function findBusRoute(from: string, to: string): BusRoute | undefined {
  return BUS_ROUTES.find((route) => route.from === from && route.to === to);
}

export function nextBusDeparture(
  route: BusRoute,
  kind: BusDayKind,
  now: Date = new Date(),
): BusDeparture | undefined {
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  return busDepartures(route, kind).find((dep) => {
    const parts = dep.time.split(":").map((part) => Number(part));
    if (parts.length < 2 || Number.isNaN(parts[0]) || Number.isNaN(parts[1])) {
      return false;
    }
    return parts[0] * 60 + parts[1] > nowMinutes;
  });
}

export function campusShortLabel(campus: string): string {
  return campus.replace("校园", "").replace("校区", "");
}
