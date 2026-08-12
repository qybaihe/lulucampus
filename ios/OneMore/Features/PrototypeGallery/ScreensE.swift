#if DEBUG
import SwiftUI

// MARK: - E · 局的全生命周期（screens-2.js）

/// E1 · 我的局 / 搭子
struct E1Screen: View {
    let actions: PrototypeActions
    @State private var seg = "进行中"

    var body: some View {
        PrototypePage(nav: "我的局", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMSeg(items: ["进行中", "已完成", "已结束"], label: { $0 }, selection: $seg)
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMRow(sticker: "trophy.png", title: "数学建模国赛冲刺", sub: "周五 19:00 · 研讨间 4C 已订", onTap: { prototypeGo("E2", actions) }) {
                        OMChip(text: "已成局", kind: .solid)
                    }
                    OMRow(sticker: "basketball.png", title: "周五晚篮球半场", sub: "匿名招募中 · 截止周五 12:00", onTap: { prototypeGo("D4", actions) }) {
                        OMChip(text: "缺 2", kind: .gap)
                    }
                    OMRow(sticker: "books-stack.png", title: "操作系统考前冲刺", sub: "3 人已确认 · 等你确认", onTap: { prototypeGo("E3", actions) }) {
                        OMGapBadge(text: "差你 1 票")
                    }
                }
                OMSection(title: "已安静结束")
                OMCard(tight: true) {
                    OMRow(sticker: "table-tennis.png", title: "上周乒乓球双打", sub: "未凑齐 · 已安静解散", onTap: { prototypeGo("G4", actions) }) {
                        OMChip(text: "已结束")
                    }
                }
            }
        }
    }
}

/// E2 · 局详情容器
struct E2Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(
            nav: "局详情", back: true, backTarget: .e1,
            navRight: AnyView(OMIconButton(icon: .share, accessibilityLabel: "分享缺口卡") { prototypeGo("G2", actions) }),
            actions: actions
        ) {
            VStack(spacing: 0) {
                OMSeatTable(name: "数学建模国赛冲刺", seats: [
                    OMSeat(role: "建模", state: .filled, sticker: "data-chart.png"),
                    OMSeat(role: "编程", state: .filled, sticker: "algorithm-gear.png"),
                    OMSeat(role: "写作", state: .filled, sticker: "marker.png"),
                ], tableSticker: "trophy.png")

                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "周五 19:00–21:30", sub: "图书馆 4F 研讨间 4C · 已订", onTap: { prototypeGo("E4", actions) }) {
                        OMChip(text: "改约")
                    }
                    OMRow(sticker: "round-table.png", title: "协作空间", sub: "时间地点 · 角色待办 · 群聊", onTap: { prototypeGo("E7", actions) })
                    OMRow(sticker: "trophy.png", title: "共同目标", sub: "长期局：整个赛季的训练与参赛", onTap: { prototypeGo("E11", actions) })
                }
                HStack(spacing: 8) {
                    OMButton("退出这个局", kind: .ghost, small: true) { prototypeGo("E12", actions) }
                    OMButton("举报与拉黑", kind: .text, small: true) { prototypeGo("E13", actions) }
                }
            }
        }
    }
}

/// E3 · 多人确认
struct E3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "多人确认", back: true, backTarget: .e1, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认加入") { prototypeGo("E5", actions) }
                OMButton("这次不参加", kind: .text) { prototypeGo("E1", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .confirmGather, placement: .confirm)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t2("就差你确认了")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("操作系统考前冲刺 · 周四 19:00 · 图书馆 4C")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)
                OMCard {
                    OMReadiness(ready: 3, total: 4)
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "3 个席位已确认", detail: "双向确认完成前，彼此匿名"),
                        OMTimelineItem(state: .now, title: "你的确认", detail: "截止今晚 22:00 · 剩 4 小时 12 分"),
                    ])
                    .padding(.top, OMTheme.Spacing.s4)
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "确认即同意时间地点与安全偏好。超时未确认，席位自动让出，不会有任何人知道你被邀请过。", sticker: "hourglass.png")
            }
        }
    }
}

/// E4 · 改约协商
struct E4Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "改约协商", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    OMTextRole.t3("提议改约")
                    OMTextRole.foot("当前：周五 19:00–21:30 · 图书馆 4C").padding(.top, 4)
                    OMDivider()
                    OMRow(icon: .clock, title: "改为：周六 15:00–17:30", sub: "提议人：建模位成员 · 理由：周五临时有实验") {
                        OMChip(text: "待表态", kind: .gap)
                    }
                }
                OMCard(tight: true) {
                    OMTextRole.t3("表态情况").padding(.bottom, OMTheme.Spacing.s2)
                    OMRow(sticker: "data-chart.png", title: "建模位", sub: "提议人") {
                        OMChip(text: "同意", kind: .solid)
                    }
                    OMRow(sticker: "algorithm-gear.png", title: "编程位", sub: "1 小时前") {
                        OMChip(text: "同意", kind: .solid)
                    }
                    OMRow(sticker: "marker.png", title: "写作位（你）", sub: "等你表态") {
                        OMChip(text: "待表态", kind: .gap)
                    }
                }
                HStack(spacing: 8) {
                    OMButton("同意改约") { toast = "已同意 · 全员通过后噜噜会重订研讨间" }
                    OMButton("保持原时间", kind: .ghost) { toast = "已表态 · 提议未通过，维持原安排" }
                }
            }
        }
        .omToast($toast)
    }
}

/// E5 · 预览与授权
struct E5Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "行动预览", back: true, backTarget: .e3, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认并授权执行") { prototypeGo("E6", actions) }
                OMButton("返回修改", kind: .text) { actions.perform(.back) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .actionPreview, placement: .confirm)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t2("授权前，最后看一遍")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("这是全流程唯一一次真实写操作")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)
                OMCard(borderColor: OMTheme.ColorToken.ink, borderWidth: 2) {
                    OMRow(sticker: "seminar-room-sign.png", title: "预订：图书馆 4F 研讨间 4C", sub: "周四 19:00–21:30 · 6 人位")
                    OMRow(sticker: "access-card.png", title: "使用账号：你本人的校园账号", sub: "占用本周研讨室额度 2.5 / 6 小时")
                    OMRow(sticker: "desk-calendar.png", title: "写入 4 位成员的日历", sub: "系统日历 · 提前 15 分钟提醒 · 仅写时间地点")
                    OMRow(icon: .shield, title: "不会做的事", sub: "不代发消息 · 不代请假 · 不涉及支付")
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "授权只对这一次有效。下次行动会重新给你看预览。", sticker: "hourglass.png")
            }
        }
    }
}

/// E6 · 执行结果
struct E6Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "执行结果", back: true, backTarget: .b1, actions: actions) {
            OMButton("进入协作空间") { prototypeGo("E7", actions) }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCelebrate, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s5)
                OMTextRole.t1("订好了")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "研讨间 4C 预订成功", detail: "周四 19:00–21:30 · 预约号 YJ-20814"),
                        OMTimelineItem(state: .done, title: "已写入 4 位成员的日历", detail: "提前 15 分钟提醒"),
                        OMTimelineItem(state: .done, title: "协作空间已开启", detail: "群聊已可用 · 噜噜已退场"),
                    ])
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "如果失败：噜噜会说明卡在哪一步、已做的部分是否回滚，并给出下一步——不会只丢一个错误码。", sticker: "chat-bubble.png")
            }
        }
    }
}

/// E7 · 协作空间（Lulu 退场点）
struct E7Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "协作空间", back: true, backTarget: .e2, actions: actions) {
            OMButton("进入群聊") { prototypeGo("E14", actions) }
        } content: {
            VStack(spacing: 0) {
                OMCard(background: OMTheme.ColorToken.gapSoft, borderColor: OMTheme.ColorToken.yolk) {
                    HStack(alignment: .top, spacing: 10) {
                        LuluView(clip: .exitBow, placement: .confirm)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t3("事办完了，我先走啦")
                            OMTextRole.foot("场订好了、日历写好了。接下来是你们自己的事——噜噜已退场，这个空间里不再有 AI。")
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "周四 19:00–21:30", sub: "图书馆 4F 研讨间 4C · 预约号 YJ-20814")
                    OMRow(sticker: "data-chart.png", title: "建模位", sub: "待办：整理近 3 年赛题类型") {
                        OMChip(text: "已就位", kind: .solid)
                    }
                    OMRow(sticker: "algorithm-gear.png", title: "编程位", sub: "待办：搭好求解代码框架") {
                        OMChip(text: "已就位", kind: .solid)
                    }
                    OMRow(sticker: "marker.png", title: "写作位（你）", sub: "待办：准备论文模板") {
                        OMChip(text: "已就位", kind: .solid)
                    }
                }
            }
        }
    }
}

/// E8 · 补位面板
struct E8Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "补位", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                OMButton("分享补位缺口卡") { prototypeGo("G2", actions) }
                OMButton("缩小规模继续", kind: .ghost) { toast = "已改为 2 人局（演示）" }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .poolWaiting, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t2("有人退出，缺口重新打开")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("编程位空出来了 · 补位招募已自动重启")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)
                OMSeatTable(name: "数学建模国赛冲刺", seats: [
                    OMSeat(role: "建模", state: .filled, sticker: "data-chart.png"),
                    OMSeat(role: "编程", state: .gap, sticker: "algorithm-gear.png"),
                    OMSeat(role: "写作", state: .filled, sticker: "marker.png"),
                ], tableSticker: "trophy.png")
                OMNote(text: "退出不需要理由，也不会公示是谁退出。缺口重新匿名招募，和第一次一样。", sticker: "access-card.png")
            }
        }
        .omToast($toast)
    }
}

/// E9 · 完成确认
struct E9Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "完成确认", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .homeReply, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("这次局，成了吗？")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.foot("数学建模国赛冲刺 · 周四研讨")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)
                OMCard {
                    OMRow(sticker: "approval-stamp.png", title: "完成了", sub: "人到齐，事办完", onTap: { prototypeGo("E10", actions) })
                    OMRow(sticker: "hourglass.png", title: "部分完成", sub: "有人没到或提前结束", onTap: { prototypeGo("E10", actions) })
                    OMRow(sticker: "envelope.png", title: "没能进行", sub: "不追责，只记录事实", onTap: { prototypeGo("E10", actions) })
                }
                .padding(.top, OMTheme.Spacing.s5)
                OMNote(text: "完成确认只影响你自己的信任进度，不会给别人打分、写评价。", sticker: "access-card.png")
            }
        }
    }
}

/// E10 · 复局选择
struct E10Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "复局选择", back: true, backTarget: .e9, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .coreCelebrate, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("下次呢？")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMRow(sticker: "round-table.png", title: "再来一次", sub: "原班人马，下周同一时间", onTap: { prototypeGo("D3", actions) })
                    OMRow(sticker: "chair-empty.png", title: "换人再来", sub: "保留局的框架，重新招募", onTap: { prototypeGo("D3.3", actions) })
                    OMRow(sticker: "certificate.png", title: "就到这里", sub: "归档这次局，记住一起做过事的人", onTap: { prototypeGo("E15", actions) })
                }
                .padding(.top, OMTheme.Spacing.s5)
            }
        }
    }
}

/// E11 · 共同目标
struct E11Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "共同目标", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("trophy.png", size: .s56)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t2("数学建模 · 整个赛季")
                            OMTextRole.foot("长期局 · 8 月 12 日 → 9 月 7 日")
                        }
                    }
                    OMDivider()
                    HStack {
                        OMTextRole.foot("赛季进度")
                        Spacer()
                        OMTextRole.monoFoot("第 2 / 4 阶段")
                    }
                    .padding(.bottom, OMTheme.Spacing.s2)
                    OMProgressBar(value: 0.5)
                }
                OMCard(tight: true) {
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "组队与分工", detail: "8 月 5 日完成"),
                        OMTimelineItem(state: .done, title: "赛题类型研讨", detail: "8 月 12 日 · 研讨间 4C"),
                        OMTimelineItem(state: .now, title: "模拟赛一次", detail: "8 月 24 日前 · 场地未定"),
                        OMTimelineItem(state: .upcoming, title: "正式参赛", detail: "9 月 4–7 日"),
                    ])
                }
                OMButton("为「模拟赛」发起一次行动") { prototypeGo("D1", actions) }
            }
        }
    }
}

/// E12 · 退出 / 取消确认
struct E12Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "退出", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认退出", kind: .ghost) { prototypeGo("E8", actions) }
                OMButton("再想想") { actions.perform(.back) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("退出不需要理由")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.call("你退出后，缺口会重新匿名打开。其他成员只会看到「席位空出来了」，不会看到是谁、为什么。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 280)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard {
                    OMRow(icon: .clock, title: "距开始还有 26 小时", sub: "现在退出，补位时间充足")
                    OMRow(icon: .shield, title: "对信任进度的影响", sub: "24 小时内退出不记录；临近开始的退出会减缓升级，但不降级")
                }
                .padding(.top, OMTheme.Spacing.s5)
            }
        }
    }
}

/// E13 · 举报与拉黑
struct E13Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "举报与拉黑", back: true, backTarget: .e2, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("安全出口一直开着")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMRow(icon: .flag, title: "举报这个局", sub: "内容违规、虚假招募、安全问题") {
                        Text("›").font(.system(size: 15, weight: .bold)).foregroundStyle(OMTheme.ColorToken.sage)
                    }
                    OMRow(icon: .flag, title: "举报成员", sub: "双向确认后才可选择具体成员") {
                        Text("›").font(.system(size: 15, weight: .bold)).foregroundStyle(OMTheme.ColorToken.sage)
                    }
                    OMRow(icon: .exit, title: "拉黑并退出", sub: "对方不会再出现在你的任何局里", onTap: { prototypeGo("M8", actions) })
                }
                .padding(.top, OMTheme.Spacing.s5)
                OMNote(text: "举报由真人审核。紧急安全问题请直接联系学校保卫处 020-84110110。", sticker: "access-card.png")
            }
        }
    }
}

/// E14 · 局内群聊（Lulu 不出场）
struct E14Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(
            nav: "数学建模国赛冲刺", back: true, backTarget: .msg,
            sheet: AnyView(OMChatInputBar(placeholder: "发消息…")),
            actions: actions
        ) {
            VStack(spacing: 0) {
                VStack(spacing: 10) {
                    OMSysBubble(text: "研讨间 4C 已订好 · 周四 19:00 · 噜噜已退场")
                    OMChatBubble("论文模板我传到群文件了，用的是去年国一的格式", mine: false)
                    OMChatBubble("收到，我今晚把摘要部分先搭起来", mine: true)
                    OMChatBubble("模拟赛定在下周六下午怎么样？我看了看大家空档都合适", mine: false)
                    OMChatBubble("可以，周六下午我没课", mine: true)
                }
                .padding(.top, OMTheme.Spacing.s3)
                OMNote(text: "这个群聊里没有 AI。没有已读回执，没有在线状态，没有「正在输入」。", sticker: "access-card.png")
                    .padding(.top, OMTheme.Spacing.s4)
            }
        }
    }
}

/// E15 · 搭子关系列表
struct E15Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "搭子关系", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMTextRole.foot("一起做成过事的人。只记事实，不记评价。")
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMRow(sticker: "data-chart.png", title: "一起打过 2 个局", sub: "数学建模 × 2 · 最近：8 月 12 日", onTap: { prototypeGo("E16", actions) })
                    OMRow(sticker: "basketball.png", title: "一起打过 1 个局", sub: "篮球半场 · 最近：7 月 28 日", onTap: { prototypeGo("E16", actions) })
                }
                OMNote(text: "没有「最常一起的人」排行，没有搭子数量统计。关系是事实记录，不是社交资本。", sticker: "access-card.png")
            }
        }
    }
}

/// E16 · 搭子关系详情
struct E16Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "共同经历", back: true, backTarget: .e15, actions: actions) {
            OMButton("解除搭子关系", kind: .ghost) { prototypeGo("E17", actions) }
        } content: {
            VStack(spacing: 0) {
                OMTextRole.foot("你们一起做过的事。只有事实，没有印象分。")
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "数学建模国赛冲刺", detail: "8 月 12 日 · 研讨间 4C · 已完成"),
                        OMTimelineItem(state: .done, title: "数学建模校内热身赛", detail: "6 月 20 日 · 线上 · 已完成"),
                    ])
                }
                OMNote(text: "这里不会出现「靠谱」「准时」这类评价标签——共同经历只回答「一起做过什么」。", sticker: "chat-bubble.png")
            }
        }
    }
}

/// E17 · 解除关系
struct E17Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "解除关系", back: true, backTarget: .e16, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认解除", kind: .ghost) { prototypeGo("E15", actions) }
                OMButton("再想想") { actions.perform(.back) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("单向解除，立即生效")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.call("解除后：共同经历保留事实但不再关联彼此；对方不会收到通知；你们不会再被匹配进同一个局。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 280)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard {
                    OMRow(icon: .shield, title: "对方看到的", sub: "什么都没有。没有通知，没有提示")
                    OMRow(icon: .exit, title: "可以恢复吗", sub: "不可以。再次成局需要重新双向确认")
                }
                .padding(.top, OMTheme.Spacing.s5)
            }
        }
    }
}
#endif
