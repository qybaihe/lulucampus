import Foundation

/// B9 班车离线时刻表。数据来源：sysu-anything `data/bus-schedule.json`（广州校内班车，
/// 2026-08-12 快照）与岐关车实时班次快照（已核对工作日与周六一致）。班次常年不变，
/// 按产品决定硬编码；法定节假日调休以学校通知为准。
enum CampusBusSchedule {
    enum DayKind: String, CaseIterable, Sendable {
        case workday = "工作日"
        case holiday = "节假日"
    }

    struct Departure: Sendable {
        let time: String
        /// 途经 / 停靠说明，如「途经黄埔大道」「中途不停」
        let via: String?
        /// 乘客范围：nil = 教职工与学生均可
        let staffOnly: Bool
        /// 到达时间（仅岐关车）
        let arrive: String?
        /// 直达 / 经停（仅岐关车）
        let express: Bool

        static func shuttle(_ time: String, _ via: String? = nil, staffOnly: Bool = false) -> Departure {
            Departure(time: time, via: via, staffOnly: staffOnly, arrive: nil, express: false)
        }
        static func qiguan(_ board: String, _ arrive: String, express: Bool) -> Departure {
            Departure(time: board, via: nil, staffOnly: false, arrive: arrive, express: express)
        }
    }

    struct Route: Identifiable, Sendable {
        let id: String
        let from: String
        let to: String
        let fromStation: String
        let toStation: String
        /// 岐关车 = 广州↔珠海公路班线，需另行购票
        let isQiguan: Bool
        let workday: [Departure]
        let holiday: [Departure]

        var title: String { "\(from) → \(to)" }
        func departures(_ kind: DayKind) -> [Departure] { kind == .workday ? workday : holiday }
    }

    static let routes: [Route] = [
        Route(id: "gz-east-north", from: "东校园", to: "北校园",
              fromStation: "兰园 3 号（原生科院大楼）", toStation: "北校园南门车房楼下",
              isQiguan: false,
              workday: [
                  .shuttle("7:00", "途经黄埔大道", staffOnly: true),
                  .shuttle("8:00", "途经黄埔大道"),
                  .shuttle("10:00", "途经黄埔大道"),
                  .shuttle("12:10", "途经黄埔大道"),
                  .shuttle("15:30", "途经黄埔大道"),
                  .shuttle("16:20", "途经黄埔大道"),
                  .shuttle("17:10", "途经黄埔大道", staffOnly: true),
                  .shuttle("18:30", "途经黄埔大道", staffOnly: true),
                  .shuttle("21:00", "途经黄埔大道"),
                  .shuttle("21:55", "途经黄埔大道"),
              ],
              holiday: [
                  .shuttle("9:30", "途经黄埔大道"),
                  .shuttle("13:30", "途经黄埔大道"),
              ]),
        Route(id: "gz-north-east", from: "北校园", to: "东校园",
              fromStation: "北校园南门车房楼下", toStation: "兰园 3 号（原生科院大楼）",
              isQiguan: false,
              workday: [
                  .shuttle("7:00", "途经黄埔大道", staffOnly: true),
                  .shuttle("7:50", "途经黄埔大道", staffOnly: true),
                  .shuttle("8:10", "途经黄埔大道", staffOnly: true),
                  .shuttle("9:00", "途经黄埔大道"),
                  .shuttle("9:40", "途经黄埔大道"),
                  .shuttle("13:10", "途经黄埔大道"),
                  .shuttle("15:10", "途经黄埔大道"),
                  .shuttle("17:45", "途经黄埔大道", staffOnly: true),
                  .shuttle("18:50", "途经黄埔大道"),
                  .shuttle("20:50", "途经黄埔大道"),
              ],
              holiday: [
                  .shuttle("8:20", "途经黄埔大道"),
                  .shuttle("12:40", "途经黄埔大道"),
              ]),
        Route(id: "gz-east-south", from: "东校园", to: "南校园",
              fromStation: "兰园 3 号（原生科院大楼）", toStation: "南校园南门停车场",
              isQiguan: false,
              workday: [
                  .shuttle("7:10", "校园内经教师公寓对面", staffOnly: true),
                  .shuttle("8:00", "校园内经教师公寓对面", staffOnly: true),
                  .shuttle("10:00", "中途 1 车停坚真花园"),
                  .shuttle("12:10", "中途 1 车停坚真花园"),
                  .shuttle("13:20", "校园内经教师公寓对面"),
                  .shuttle("13:50", "校园内经教师公寓对面"),
                  .shuttle("15:30", "校园内经教师公寓对面"),
                  .shuttle("16:20", "校园内经教师公寓对面"),
                  .shuttle("17:10", "中途 1 车停坚真花园"),
                  .shuttle("18:30", "中途 1 车停坚真花园", staffOnly: true),
                  .shuttle("20:00", "校园内经教师公寓对面"),
                  .shuttle("21:00", "校园内经教师公寓对面"),
                  .shuttle("21:55", "校园内经教师公寓对面", staffOnly: true),
                  .shuttle("22:15", "校园内经教师公寓对面"),
              ],
              holiday: [
                  .shuttle("9:30", "校园内经教师公寓对面"),
                  .shuttle("13:30", "校园内经教师公寓对面"),
              ]),
        Route(id: "gz-south-east", from: "南校园", to: "东校园",
              fromStation: "南校园南门停车场", toStation: "兰园 3 号（原生科院大楼）",
              isQiguan: false,
              workday: [
                  .shuttle("7:10", "中途 1 车停坚真花园", staffOnly: true),
                  .shuttle("8:00", "中途不停"),
                  .shuttle("8:20", "中途 1 车停坚真花园"),
                  .shuttle("9:10", "中途 1 车停坚真花园"),
                  .shuttle("9:50", "中途不停"),
                  .shuttle("11:00", "中途不停"),
                  .shuttle("13:20", "中途 1 车停坚真花园"),
                  .shuttle("15:20", "中途 1 车停坚真花园"),
                  .shuttle("17:45", "中途不停", staffOnly: true),
                  .shuttle("18:00", "中途停坚真花园", staffOnly: true),
                  .shuttle("19:00", "中途不停"),
                  .shuttle("21:00", "中途不停"),
                  .shuttle("21:50", "中途不停"),
              ],
              holiday: [
                  .shuttle("8:20", "中途不停"),
                  .shuttle("12:40", "中途不停"),
              ]),
        Route(id: "gz-north-south", from: "北校园", to: "南校园",
              fromStation: "北校园南门车房楼下", toStation: "南校园南门停车场",
              isQiguan: false,
              workday: [
                  .shuttle("7:30", "途经东川路、海印桥", staffOnly: true),
                  .shuttle("9:00", "中途不停", staffOnly: true),
                  .shuttle("10:00", "中途不停", staffOnly: true),
                  .shuttle("12:10", "途经东川路、海印桥", staffOnly: true),
                  .shuttle("14:10", "途经东川路、海印桥", staffOnly: true),
                  .shuttle("15:30", "中途不停", staffOnly: true),
                  .shuttle("17:45", "途经东川路、海印桥", staffOnly: true),
              ],
              holiday: []),
        Route(id: "gz-south-north", from: "南校园", to: "北校园",
              fromStation: "南校园南门停车场", toStation: "北校园南门车房楼下",
              isQiguan: false,
              workday: [
                  .shuttle("7:30", "途经怡乐路口、海印桥", staffOnly: true),
                  .shuttle("9:30", "中途不停", staffOnly: true),
                  .shuttle("10:30", "中途不停", staffOnly: true),
                  .shuttle("12:10", "途经怡乐路口、海印桥", staffOnly: true),
                  .shuttle("14:10", "途经怡乐路口、海印桥", staffOnly: true),
                  .shuttle("16:15", "中途不停", staffOnly: true),
                  .shuttle("17:45", "途经怡乐路口、海印桥", staffOnly: true),
              ],
              holiday: []),
        Route(id: "qg-south-zhuhai", from: "南校园", to: "珠海校区",
              fromStation: "南校园岐关服务部", toStation: "珠海中大岐关服务点",
              isQiguan: true,
              workday: [
                  .qiguan("9:00", "10:40", express: true),
                  .qiguan("12:00", "13:40", express: false),
                  .qiguan("15:00", "16:40", express: true),
                  .qiguan("17:30", "19:10", express: false),
                  .qiguan("19:00", "20:40", express: true),
              ],
              holiday: [
                  .qiguan("9:00", "10:40", express: true),
                  .qiguan("12:00", "13:40", express: false),
                  .qiguan("15:00", "16:40", express: true),
                  .qiguan("17:30", "19:10", express: false),
                  .qiguan("19:00", "20:40", express: true),
              ]),
        Route(id: "qg-zhuhai-south", from: "珠海校区", to: "南校园",
              fromStation: "珠海中大岐关服务点", toStation: "南校园岐关服务部",
              isQiguan: true,
              workday: [
                  .qiguan("8:15", "9:55", express: false),
                  .qiguan("12:00", "13:40", express: true),
                  .qiguan("14:30", "16:10", express: false),
                  .qiguan("16:30", "18:10", express: true),
                  .qiguan("17:30", "19:10", express: true),
              ],
              holiday: [
                  .qiguan("8:15", "9:55", express: false),
                  .qiguan("12:00", "13:40", express: true),
                  .qiguan("14:30", "16:10", express: false),
                  .qiguan("16:30", "18:10", express: true),
                  .qiguan("17:30", "19:10", express: true),
              ]),
        Route(id: "qg-east-zhuhai", from: "东校园", to: "珠海校区",
              fromStation: "东校园（大学城）岐关服务部", toStation: "珠海中大岐关服务点",
              isQiguan: true,
              workday: [
                  .qiguan("12:30", "13:40", express: false),
                  .qiguan("18:00", "19:10", express: false),
              ],
              holiday: [
                  .qiguan("12:30", "13:40", express: false),
                  .qiguan("18:00", "19:10", express: false),
              ]),
        Route(id: "qg-zhuhai-east", from: "珠海校区", to: "东校园",
              fromStation: "珠海中大岐关服务点", toStation: "东校园（大学城）岐关服务部",
              isQiguan: true,
              workday: [
                  .qiguan("8:15", "9:35", express: false),
                  .qiguan("14:30", "15:50", express: false),
              ],
              holiday: [
                  .qiguan("8:15", "9:35", express: false),
                  .qiguan("14:30", "15:50", express: false),
              ]),
    ]

    /// 当天对应的班次类型：周末按节假日；法定节假日调休不识别，页面有脚注说明。
    static func dayKind(for date: Date = .now, calendar: Calendar = .current) -> DayKind {
        let weekday = calendar.component(.weekday, from: date)
        return (weekday == 1 || weekday == 7) ? .holiday : .workday
    }

    /// 今天还没发车的下一班（所选类型与今天一致时才有意义）。
    static func nextDeparture(on route: Route, kind: DayKind, now: Date = .now, calendar: Calendar = .current) -> Departure? {
        let nowMinutes = calendar.component(.hour, from: now) * 60 + calendar.component(.minute, from: now)
        return route.departures(kind).first { dep in
            let parts = dep.time.split(separator: ":").compactMap { Int($0) }
            guard parts.count == 2 else { return false }
            return parts[0] * 60 + parts[1] > nowMinutes
        }
    }
}
