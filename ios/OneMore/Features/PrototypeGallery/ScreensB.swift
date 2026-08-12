#if DEBUG
import SwiftUI

// MARK: - B · 今天与校园工具（screens-1.js）

/// B1 · 今天 / hermes（Tab 根）
struct B1Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(
            nav: "",
            navRight: AnyView(OMIconButton(icon: .spark, accessibilityLabel: "问 \(AppBrand.agentName)") { prototypeGo("G1", actions) }),
            large: "今天", largeSub: "8 月 12 日 · 周三 · 东校园",
            tab: .today,
            actions: actions
        ) {
            VStack(spacing: 0) {
                OMCard {
                    HStack(alignment: .top, spacing: 10) {
                        LuluView(clip: .homeReply, placement: .confirm)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t3("图书馆 4 楼今晚空着")
                            OMTextRole.foot("你的《操作系统》作业周四截止，19:00–21:30 正好是你的空档。")
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    HStack(spacing: 8) {
                        OMButton("一键发起研讨局", small: true, fillsWidth: false) { prototypeGo("B10", actions) }
                        OMButton("忽略", kind: .text, small: true, fillsWidth: false) { toast = "已忽略，不会重复提醒" }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .omCardTap("B10", actions)

                OMSection(title: "今日日程", more: ("课表", { prototypeGo("B3", actions) }))
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "数据结构与算法", sub: "10:00–11:40 · 教学楼 B204", onTap: { prototypeGo("B3.1", actions) }) {
                        OMChip(text: "1 小时后")
                    }
                    OMRow(icon: .clock, title: "大学体育 · 羽毛球", sub: "16:00–17:30 · 体育馆 2 号场", onTap: { prototypeGo("B3.1", actions) })
                }

                OMSection(title: "待确认")
                OMCard(tight: true) {
                    OMRow(sticker: "hourglass.png", title: "数学建模 · 还差你的确认", sub: "4 人局 · 剩 3 人已确认 · 截止今晚 22:00", onTap: { prototypeGo("E3", actions) }) {
                        OMGapBadge(text: "差你 1 票")
                    }
                }
                .omCardTap("E3", actions)

                OMSection(title: "校园工具")
                OMCard(tight: true) {
                    OMRow(sticker: "books-stack.png", title: "我的课表", sub: "本周 6 门课", onTap: { prototypeGo("B3", actions) })
                    OMRow(sticker: "alarm-clock.png", title: "作业与 DDL", sub: "2 个本周截止", onTap: { prototypeGo("B4", actions) }) {
                        OMChip(text: "1 紧急", kind: .gap)
                    }
                    OMRow(sticker: "badminton.png", title: "体育场馆", sub: "羽毛球今晚有空场", onTap: { prototypeGo("B5", actions) })
                    OMRow(sticker: "seminar-room-sign.png", title: "研讨室", sub: "图书馆 4 楼当前空闲 3 间", onTap: { prototypeGo("B6", actions) })
                    OMRow(sticker: "poster-blank.png", title: "校园活动", sub: "本周 12 场", onTap: { prototypeGo("B7", actions) })
                    OMRow(sticker: "notebook-open.png", title: "组会与课题", sub: "周五 14:00 导师组会", onTap: { prototypeGo("B8", actions) })
                    OMRow(sticker: "school-bus.png", title: "班车与节次", sub: "东校园 ⇄ 南校园", onTap: { prototypeGo("B9", actions) })
                }

                OMSection(title: "我的局", more: ("全部", { prototypeGo("E1", actions) }))
                OMCard(tight: true) {
                    OMRow(sticker: "trophy.png", title: "数学建模国赛冲刺", sub: "已订研讨室 · 周五 19:00", onTap: { prototypeGo("E2", actions) }) {
                        OMChip(text: "已成局", kind: .solid)
                    }
                    OMRow(sticker: "basketball.png", title: "周五晚篮球半场", sub: "匿名招募中", onTap: { prototypeGo("D4", actions) }) {
                        OMChip(text: "缺 2", kind: .gap)
                    }
                }
            }
        }
        .omToast($toast)
    }
}

/// B2 · hermes 问答
struct B2Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: AppBrand.agentName, back: true, actions: actions) {
            VStack(spacing: 0) {
                HStack(spacing: 8) {
                    TextField("问校园相关的事…", text: .constant(""))
                        .font(OMTheme.TypeToken.callout)
                        .padding(.horizontal, OMTheme.Spacing.s4)
                        .frame(minHeight: 44)
                        .background(OMTheme.ColorToken.card)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
                        .overlay {
                            RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                    OMIconButton(icon: .mic, size: 44, accessibilityLabel: "语音输入") {}
                }
                OMTextRole.cap("只回答校园事实与可用性 · 不评价人")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .homeListening, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                VStack(spacing: 10) {
                    OMChatBubble("明天下午南校园图书馆开吗？", mine: true)
                    OMChatBubble("开。明天是工作日，南校园图书馆 8:00–22:30 开放。你 14:00–17:00 没课，要帮你看看研讨室吗？", mine: false)
                    OMChatBubble("周五晚上体育馆羽毛球还有场吗？", mine: true)
                    OMChatBubble("有。周五 19:00–21:00 还剩 2 片羽毛球场。你周五 16:00 后没课——要订的话我会先给你看预览，确认后才下单。", mine: false)
                }
                .padding(.top, OMTheme.Spacing.s4)
            }
        }
    }
}

/// B3 · 我的课表
struct B3Screen: View {
    let actions: PrototypeActions
    @State private var seg = "本周"

    var body: some View {
        PrototypePage(nav: "我的课表", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMSeg(items: ["本周", "下周", "整学期"], label: { $0 }, selection: $seg)
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMScheduleGrid(rows: [
                        [.init(.head), .init(.head, "一"), .init(.head, "二"), .init(.head, "三"), .init(.head, "四"), .init(.head, "五")],
                        [.init(.time, "1-2"), .init(.empty), .init(.has, "高等数学", onTap: { prototypeGo("B3.1", actions) }), .init(.empty), .init(.has, "大学英语"), .init(.empty)],
                        [.init(.time, "3-4"), .init(.has, "操作系统"), .init(.empty), .init(.has, "数据结构", onTap: { prototypeGo("B3.1", actions) }), .init(.empty), .init(.has, "概率论")],
                        [.init(.time, "5-6"), .init(.free, "空档"), .init(.has, "体育"), .init(.free, "空档"), .init(.has, "毛概"), .init(.free, "空档")],
                        [.init(.time, "7-8"), .init(.empty), .init(.empty), .init(.empty), .init(.empty), .init(.empty)],
                    ])
                }
                OMNote(text: "黄色虚线格是你的固定空档——噜噜只在这些时间里帮你攒局。课表来自教务系统，别人看不到。", sticker: "desk-calendar.png")
            }
        }
    }
}

/// B3.1 · 课程详情
struct B31Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "课程详情", back: true, backTarget: .b3, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("books-stack.png", size: .s56)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t2("数据结构与算法")
                            OMTextRole.foot("CS2101 · 3 学分 · 必修")
                        }
                    }
                    OMDivider()
                    OMRow(icon: .clock, title: "周三 10:00–11:40", sub: "第 1–16 周")
                    OMRow(icon: .pin, title: "东校园 教学楼 B204", sub: "距你当前位置步行约 6 分钟")
                    OMRow(icon: .doc, title: "作业 3：二叉树遍历", sub: "周四 23:59 截止", onTap: { prototypeGo("B4.1", actions) }) {
                        OMChip(text: "明天截止", kind: .gap)
                    }
                }
                OMNote(text: "这里不会出现同课同学名单。想找人一起复习，可以从作业详情发起一个局。", sticker: "access-card.png")
                OMButton("就这门课发起复习局") { prototypeGo("D1", actions) }
                    .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// B4 · 作业与 DDL
struct B4Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "作业与 DDL", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true, borderColor: OMTheme.ColorToken.yolk, borderWidth: 2) {
                    OMRow(sticker: "alarm-clock.png", title: "作业 3：二叉树遍历", sub: "数据结构与算法 · 剩 31 小时", onTap: { prototypeGo("B4.1", actions) }) {
                        OMChip(text: "最紧急", kind: .gap)
                    }
                }
                OMCard(tight: true) {
                    OMRow(sticker: "notebook-open.png", title: "实验报告 2", sub: "操作系统 · 剩 4 天", onTap: { prototypeGo("B4.1", actions) })
                    OMRow(sticker: "marker.png", title: "英语视听说 Unit 5", sub: "大学英语 · 剩 6 天", onTap: { prototypeGo("B4.1", actions) })
                }
                OMNote(text: "按剩余时间排序，不按课程重要度打分。DDL 来自教务系统与课程群公告的公开信息。", sticker: "hourglass.png")
            }
        }
    }
}

/// B4.1 · 作业详情
struct B41Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "作业详情", back: true, backTarget: .b4, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    OMTextRole.t2("作业 3：二叉树遍历")
                    OMTextRole.foot("数据结构与算法 · 周四 23:59 截止").padding(.top, 4)
                    OMGapHero(31, suffix: "小时后截止").padding(.top, OMTheme.Spacing.s4)
                    OMDivider()
                    OMTextRole.call("实现前序 / 中序 / 后序遍历的递归与非递归版本，提交 PDF 报告与源码。占平时成绩 10%。")
                }
                OMCard {
                    OMTextRole.t3("你的空档里，这两段最适合").padding(.bottom, OMTheme.Spacing.s2)
                    OMRow(icon: .clock, title: "今晚 19:00–21:30", sub: "图书馆 4 楼研讨室当前有空") {
                        OMButton("发起研讨局", small: true, fillsWidth: false) { prototypeGo("B10", actions) }
                    }
                    OMRow(icon: .clock, title: "明天 14:00–17:00", sub: "宿舍 / 自习均可") {
                        OMButton("单人行动", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                }
            }
        }
    }
}

/// B5 · 体育场馆
struct B5Screen: View {
    let actions: PrototypeActions
    @State private var days: [OMCalDay] = [
        OMCalDay(id: "12", day: "12", weekday: "今天", dots: 1),
        OMCalDay(id: "13", day: "13", weekday: "周四", selected: true, dots: 2),
        OMCalDay(id: "14", day: "14", weekday: "周五", dots: 1),
        OMCalDay(id: "15", day: "15", weekday: "周六", dots: 0),
        OMCalDay(id: "16", day: "16", weekday: "周日", dots: 2),
    ]

    var body: some View {
        PrototypePage(nav: "体育场馆", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMCalStrip(days: days) { tapped in
                    days = days.map { $0.id == tapped.id ? OMCalDay(id: $0.id, day: $0.day, weekday: $0.weekday, selected: true, dots: $0.dots)
                        : OMCalDay(id: $0.id, day: $0.day, weekday: $0.weekday, selected: false, dots: $0.dots) }
                }
                .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMRow(sticker: "badminton.png", title: "羽毛球馆", sub: "东校园体育馆 2F", onTap: { prototypeGo("B5.1", actions) }) {
                        OMChip(text: "今晚有空", kind: .gap)
                    }
                    OMRow(sticker: "basketball.png", title: "篮球场", sub: "东校园室外场", onTap: { prototypeGo("B5.1", actions) }) {
                        OMChip(text: "3 片空")
                    }
                    OMRow(sticker: "table-tennis.png", title: "乒乓球馆", sub: "东校园体育馆 1F", onTap: { prototypeGo("B5.1", actions) }) {
                        OMChip(text: "已满")
                    }
                    OMRow(sticker: "football.png", title: "足球场", sub: "东校园真草场", onTap: { prototypeGo("B5.1", actions) }) {
                        OMChip(text: "1 片空")
                    }
                }
                OMNote(text: "只显示场地有没有空，不显示「现在谁在场」。", sticker: "access-card.png")
            }
        }
    }
}

/// B5.1 · 场馆时段选择
struct B51Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "羽毛球馆 · 时段", back: true, backTarget: .b5, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "18:00–19:00", sub: "2 号场 · 4 人半场") {
                        OMButton("选这个", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                    OMRow(icon: .clock, title: "19:00–20:00", sub: "2 号场 · 4 人半场") {
                        OMButton("选这个", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                    OMRow(icon: .clock, title: "20:00–21:00", sub: "5 号场 · 可包场") {
                        OMButton("选这个", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                }
                OMCard {
                    HStack(alignment: .top, spacing: 10) {
                        LuluView(clip: .homeReply, placement: .confirm)
                        (Text("一个人订场可以直接订；")
                        + Text("缺球友的话，我可以顺手帮你开个局").bold()
                        + Text("，人齐了一起订。"))
                            .font(OMTheme.TypeToken.callout)
                            .lineSpacing(3)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                OMButton("差球友，开个局") { prototypeGo("D1", actions) }
            }
        }
    }
}

/// B6 · 图书馆研讨室
struct B6Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "研讨室", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "seminar-room-sign.png", title: "图书馆 4F · 研讨间", sub: "4–8 人 · 白板 · 插座", onTap: { prototypeGo("B6.1", actions) }) {
                        OMChip(text: "3 间空闲", kind: .gap)
                    }
                    OMRow(sticker: "study-lamp.png", title: "图书馆 6F · 静音研讨间", sub: "2–4 人 · 需安静", onTap: { prototypeGo("B6.1", actions) }) {
                        OMChip(text: "1 间空闲")
                    }
                    OMRow(sticker: "teaching-building.png", title: "教学楼 C 区 · 讨论室", sub: "6–10 人 · 可投影", onTap: { prototypeGo("B6.1", actions) }) {
                        OMChip(text: "今晚全满")
                    }
                }
                OMNote(text: "研讨室预约以学校图书馆系统为准。噜噜只做代预约，且每次都会先给你看预览。", sticker: "chat-bubble.png")
            }
        }
    }
}

/// B6.1 · 研讨室时段选择
struct B61Screen: View {
    let actions: PrototypeActions
    @State private var days: [OMCalDay] = [
        OMCalDay(id: "12", day: "12", weekday: "今天", selected: true, dots: 1),
        OMCalDay(id: "13", day: "13", weekday: "周四", dots: 1),
        OMCalDay(id: "14", day: "14", weekday: "周五", dots: 0),
    ]

    var body: some View {
        PrototypePage(nav: "图书馆 4F · 选时段", back: true, backTarget: .b6, actions: actions) {
            VStack(spacing: 0) {
                OMCalStrip(days: days) { tapped in
                    days = days.map { $0.id == tapped.id ? OMCalDay(id: $0.id, day: $0.day, weekday: $0.weekday, selected: true, dots: $0.dots)
                        : OMCalDay(id: $0.id, day: $0.day, weekday: $0.weekday, selected: false, dots: $0.dots) }
                }
                .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "14:00–16:00", sub: "研讨间 4B · 6 人位") {
                        OMButton("选", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                    OMRow(icon: .clock, title: "16:00–18:00", sub: "研讨间 4A · 8 人位") {
                        OMButton("选", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("B11", actions) }
                    }
                    OMRow(icon: .clock, title: "19:00–21:30", sub: "研讨间 4C · 6 人位 · 与你的空档重合") {
                        OMChip(text: "推荐", kind: .gap)
                    }
                }
                OMButton("用 19:00–21:30 发起研讨局") { prototypeGo("B10", actions) }
            }
        }
    }
}

/// B7 · 活动 / 宣讲会
struct B7Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "校园活动", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMNote(text: "未登录也能浏览这一页。报名才需要认证。", sticker: "poster-blank.png")
                OMCard(tight: true) {
                    OMRow(sticker: "poster-blank.png", title: "「人工智能+X」交叉学科讲座", sub: "周四 15:00 · 南校园梁銶琚堂", onTap: { prototypeGo("B7.1", actions) })
                    OMRow(sticker: "poster-blank.png", title: "社团招新夜市", sub: "周五 18:30 · 东校园生活区广场", onTap: { prototypeGo("B7.1", actions) })
                    OMRow(sticker: "poster-blank.png", title: "校友分享：从实验室到创业", sub: "周六 10:00 · 珠海校区", onTap: { prototypeGo("B7.1", actions) })
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// B7.1 · 活动详情
struct B71Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "活动详情", back: true, backTarget: .b7, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    OMSticker("poster-blank.png", size: .s96)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 28)
                        .background(OMTheme.ColorToken.ink06)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
                    OMTextRole.t2("「人工智能+X」交叉学科讲座").padding(.top, OMTheme.Spacing.s3)
                    OMTextRole.foot("主办：计算机学院 · 周四 15:00–17:00 · 南校园梁銶琚堂").padding(.top, 4)
                    OMTextRole.call("四位来自医学、法学、材料与计算机的老师，各用 15 分钟讲一个 AI 进入自己学科的真实案例。")
                        .padding(.top, OMTheme.Spacing.s3)
                }
                OMButton("去不去，先放进日程看看") { toast = "已加入今日日程（演示）" }
                OMButton("想找同去的人，开个局", kind: .ghost) { prototypeGo("D1", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
        .omToast($toast)
    }
}

/// B8 · 组会与课题
struct B8Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "组会与课题", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "notebook-open.png", title: "导师组会", sub: "周五 14:00–16:00 · 计算机学院楼 A501") {
                        OMChip(text: "本周", kind: .solid)
                    }
                    OMRow(sticker: "laptop-closed.png", title: "课题：校园人流预测", sub: "下次汇报：文献综述部分") {
                        OMChip(text: "进行中")
                    }
                }
                OMNote(text: "组会信息来自你主动同步的课题组日历。App 不会替你请假，也不会替你汇报。", sticker: "access-card.png")
            }
        }
    }
}

/// B9 · 班车
struct B9Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "班车与节次", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMSection(title: "校区班车")
                OMCard(tight: true) {
                    OMRow(sticker: "school-bus.png", title: "东校园 → 南校园", sub: "下一班 14:30 · 教学楼 A 区上车") {
                        OMChip(text: "25 分钟后", kind: .gap)
                    }
                    OMRow(sticker: "school-bus.png", title: "东校园 → 珠海校区", sub: "每天 7:30 / 17:00 两班") {
                        OMChip(text: "需预约")
                    }
                }
                OMSection(title: "上课节次")
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "第 1–2 节", sub: "08:00–09:40") { OMTextRole.monoFoot("08:00") }
                    OMRow(icon: .clock, title: "第 3–4 节", sub: "10:00–11:40") { OMTextRole.monoFoot("10:00") }
                    OMRow(icon: .clock, title: "第 5–6 节", sub: "14:00–15:40") { OMTextRole.monoFoot("14:00") }
                    OMRow(icon: .clock, title: "第 7–8 节", sub: "16:00–17:40") { OMTextRole.monoFoot("16:00") }
                    OMRow(icon: .clock, title: "第 9–10 节", sub: "19:00–20:40") { OMTextRole.monoFoot("19:00") }
                }
            }
        }
    }
}

/// B10 · 场景触发浮层
struct B10Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "场景触发", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .intentCard, placement: .hero)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMCard {
                    OMTextRole.t2("图书馆 4 楼今晚空着")
                    OMTextRole.call("三个事实拼在一起：")
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "你的空档", detail: "今晚 19:00–21:30 没课"),
                        OMTimelineItem(state: .done, title: "场地空闲", detail: "图书馆 4F 研讨间 4C 当前可订"),
                        OMTimelineItem(state: .now, title: "DDL 临近", detail: "《操作系统》实验报告 剩 4 天"),
                    ])
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .padding(.top, OMTheme.Spacing.s4)
                HStack(spacing: 8) {
                    OMButton("发起研讨局") { prototypeGo("D1", actions) }
                    OMButton("忽略", kind: .ghost, fillsWidth: false) { prototypeGo("tab:today", actions) }
                }
                OMTextRole.cap("忽略后同类建议 3 天内不再出现")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }
}

/// B11 · 个人行动预览
struct B11Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "行动预览", back: true, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认并授权执行") { prototypeGo("E6", actions) }
                OMButton("再想想", kind: .text) { actions.perform(.back) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .actionPreview, placement: .confirm)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t2("确认这次单人行动")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard {
                    OMRow(sticker: "seminar-room-sign.png", title: "预订：图书馆 4F 研讨间 4C", sub: "今天 19:00–21:30")
                    OMRow(sticker: "access-card.png", title: "使用账号：你本人校园账号", sub: "占用本周研讨室额度 2.5 / 6 小时")
                    OMRow(sticker: "desk-calendar.png", title: "写入日历", sub: "系统日历 · 提前 15 分钟提醒")
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "这是唯一一次真实写操作。看清楚再授权；授权后随时可以在「我的局」里取消。", sticker: "hourglass.png")
            }
        }
    }
}

/// B12 · 赛事库（Tab 根）
struct B12Screen: View {
    let actions: PrototypeActions
    @State private var seg = "全部"

    var body: some View {
        PrototypePage(large: "比赛", largeSub: "已核验赛事 · 看出哪桌还差人", tab: .match, actions: actions) {
            VStack(spacing: 0) {
                OMSeg(items: ["全部", "我能上桌", "还差人"], label: { $0 }, selection: $seg)
                    .padding(.bottom, OMTheme.Spacing.s3)

                competitionCard(
                    title: "全国大学生数学建模竞赛", sub: "9 月 4 日开赛 · 3 人队",
                    seats: [
                        OMSeat(role: "建模", state: .filled, sticker: "data-chart.png"),
                        OMSeat(role: "编程", state: .filled, sticker: "algorithm-gear.png"),
                        OMSeat(role: "写作", state: .gap, sticker: "marker.png"),
                    ], gap: 1
                )
                competitionCard(
                    title: "ACM-ICPC 校队选拔", sub: "8 月 30 日 · 3 人队",
                    seats: [
                        OMSeat(role: "算法", state: .filled, sticker: "algorithm-gear.png"),
                        OMSeat(role: "算法", state: .gap, sticker: "algorithm-gear.png"),
                        OMSeat(role: "代码", state: .gap, sticker: "backend-server.png"),
                    ], gap: 2
                )
                competitionCard(
                    title: "「挑战杯」课外学术作品赛", sub: "10 月校赛 · 最多 8 人",
                    seats: [
                        OMSeat(role: "产品", state: .filled, sticker: "product-notes.png"),
                        OMSeat(role: "设计", state: .filled, sticker: "design-palette.png"),
                        OMSeat(role: "前端", state: .gap, sticker: "frontend-browser.png"),
                        OMSeat(role: "后端", state: .gap, sticker: "backend-server.png"),
                    ], gap: 2
                )

                OMNote(text: "「已核验」= 赛事信息经学校团委或学院官方渠道确认。席位只显示角色缺口，不显示已就位者是谁。", sticker: "approval-stamp.png")
            }
        }
    }

    private func competitionCard(title: String, sub: String, seats: [OMSeat], gap: Int) -> some View {
        OMCard {
            HStack {
                HStack(spacing: 10) {
                    OMSticker("trophy.png", size: .s44)
                    VStack(alignment: .leading, spacing: 2) {
                        OMTextRole.t3(title)
                        OMTextRole.foot(sub)
                    }
                }
                Spacer()
                OMChip(text: "已核验", kind: .solid)
            }
            HStack {
                OMSeatStrip(seats: seats)
                Spacer()
                OMGapBadge(count: gap)
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
        .omCardTap("B12.1", actions)
    }
}

/// B12.1 · 赛事详情
struct B121Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "赛事详情", back: true, backTarget: .b12, actions: actions) {
            VStack(spacing: 0) {
                OMButton("补上「写作」这席") { prototypeGo("D1", actions) }
                OMButton("自己另开一桌", kind: .ghost) { prototypeGo("D1", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                OMSticker("trophy.png", size: .s72)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.t1("全国大学生数学建模竞赛")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("9 月 4–7 日 · 3 人一队 · 校推免加分赛事")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)

                OMSeatTable(name: "数模 · 这桌 2/3 已就位", seats: [
                    OMSeat(role: "建模", state: .filled, sticker: "data-chart.png"),
                    OMSeat(role: "编程", state: .filled, sticker: "algorithm-gear.png"),
                    OMSeat(role: "写作", state: .gap, sticker: "marker.png"),
                ], tableSticker: "round-table.png")

                OMCard {
                    OMTextRole.t3("这桌需要的能力").padding(.bottom, OMTheme.Spacing.s2)
                    OMFlowLayout {
                        OMChip(text: "数学建模", kind: .solid, sticker: "data-chart.png")
                        OMChip(text: "编程实现", kind: .solid, sticker: "algorithm-gear.png")
                        OMChip(text: "论文写作 · 缺口", kind: .gap, sticker: "marker.png")
                    }
                    OMDivider()
                    OMTextRole.t3("你具备的").padding(.bottom, OMTheme.Spacing.s2)
                    OMFlowLayout {
                        OMChip(text: "算法", kind: .soft, sticker: "algorithm-gear.png")
                        OMChip(text: "后端", kind: .soft, sticker: "backend-server.png")
                    }
                    OMTextRole.foot("你的「编程实现」与这桌已就位角色重合，可以补「写作」位以外的空缺，或自己另开一桌。")
                        .padding(.top, OMTheme.Spacing.s2)
                }

                OMCard(tight: true) {
                    OMRow(icon: .cal, title: "赛程", sub: "9/4 20:00 发题 → 9/7 20:00 提交")
                    OMRow(icon: .doc, title: "组队规则", sub: "每队 3 人，可跨学院，不可跨校")
                }
            }
        }
    }
}
#endif
