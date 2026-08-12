#if DEBUG
import SwiftUI

// MARK: - MSG · 消息（Tab 根，screens-3.js）

struct MSGScreen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(large: "消息", largeSub: "只有已成局的人会出现在这里", tab: .msg, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "trophy.png", title: "数学建模国赛冲刺", sub: "「模拟赛定在下周六下午怎么样？」", onTap: { prototypeGo("E14", actions) }) {
                        OMTextRole.foot("14:02")
                    }
                    OMRow(sticker: "books-stack.png", title: "操作系统考前冲刺", sub: "「研讨间 4C 已订好 · 噜噜已退场」", onTap: { prototypeGo("E14", actions) }) {
                        OMTextRole.foot("昨天")
                    }
                }
                OMNote(text: "没有陌生人私聊，没有群二维码，没有已读回执。局结束 7 天后，群聊自动归档为只读。", sticker: "chat-bubble.png")
            }
        }
    }
}

// MARK: - M · 我（screens-3.js）

/// M1 · 我（Tab 根）
struct M1Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(large: "我", tab: .me, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    HStack(spacing: 10) {
                        LuluView(clip: .homeIdle, placement: .avatar)
                        VStack(alignment: .leading, spacing: 4) {
                            OMTextRole.t3("阿哲")
                            OMTextRole.foot("电子信息与工程学院 · 2023 级")
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        OMButton("T2", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("M3", actions) }
                    }
                    OMDivider()
                    HStack {
                        OMTextRole.foot("信任等级 T2 · 可发起公开局")
                        Spacer()
                        Button { prototypeGo("M3", actions) } label: {
                            Text("进度 →").font(OMTheme.TypeToken.footnote.weight(.semibold)).foregroundStyle(OMTheme.ColorToken.ink)
                        }
                        .buttonStyle(.plain)
                    }
                    OMProgressBar(value: 0.46).padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.cap("等级只有你自己看得见。它解锁能力，不是身份标识。")
                        .padding(.top, OMTheme.Spacing.s2)
                }

                OMSection(title: "我的")
                OMCard(tight: true) {
                    OMRow(sticker: "round-table.png", title: "我的局", sub: "3 个进行中", onTap: { prototypeGo("E1", actions) })
                    OMRow(sticker: "badge.png", title: "搭子关系", sub: "2 段共同经历", onTap: { prototypeGo("E15", actions) })
                    OMRow(sticker: "certificate.png", title: "主理人控制台", sub: "你管理的 1 个官方局", onTap: { prototypeGo("O1", actions) })
                }

                OMSection(title: "设置")
                OMCard(tight: true) {
                    OMRow(sticker: "nameplate-blank.png", title: "画像编辑", sub: "能力标签与可用时间", onTap: { prototypeGo("M2", actions) })
                    OMRow(sticker: "access-card.png", title: "授权管理", sub: "已授权 3 项", onTap: { prototypeGo("M4", actions) })
                    OMRow(icon: .shield, title: "隐私与安全", sub: "社交开关 · 可见性", onTap: { prototypeGo("M5", actions) })
                    OMRow(sticker: "chair-empty.png", title: "匹配偏好", sub: "规模 · 距离 · 时段", onTap: { prototypeGo("M6", actions) })
                    OMRow(icon: .bell, title: "通知与日历", sub: "推送 · 日历同步", onTap: { prototypeGo("M7", actions) })
                    OMRow(icon: .exit, title: "黑名单", sub: "已拉黑 0 人", onTap: { prototypeGo("M8", actions) })
                    OMRow(sticker: "envelope.png", title: "信任申诉", sub: "对等级判定提出异议", onTap: { prototypeGo("M9", actions) })
                    OMRow(icon: .gear, title: "账号与数据", sub: "导出 · 注销", onTap: { prototypeGo("M10", actions) })
                }
            }
        }
    }
}

/// M2 · 画像编辑
struct M2Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "画像编辑", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMSection(title: "能力标签")
                OMCard(tight: true) {
                    OMRow(sticker: "algorithm-gear.png", title: "算法", sub: "来源：已修《数据结构与算法》") {
                        OMChip(text: "课程", kind: .solid)
                    }
                    OMRow(sticker: "backend-server.png", title: "后端", sub: "来源：已修《操作系统》《数据库系统》") {
                        OMChip(text: "课程", kind: .solid)
                    }
                    OMRow(sticker: "design-palette.png", title: "设计", sub: "来源：你自己添加") {
                        OMChip(text: "自述")
                    }
                }
                OMButton("添加自述标签", kind: .ghost) { toast = "自述标签会明确标注来源（演示）" }
                OMSection(title: "可用时间")
                OMCard(tight: true) {
                    OMFlowLayout {
                        OMChip(text: "周二 19:00–21:30", kind: .soft)
                        OMChip(text: "周三 14:00–17:00", kind: .soft)
                        OMChip(text: "周五 16:00 后", kind: .soft)
                        OMChip(text: "周末全天", kind: .soft)
                    }
                    OMTextRole.foot("来自课表空档。课表变了这里会自动更新。")
                        .padding(.top, OMTheme.Spacing.s3)
                }
                OMNote(text: "课程来源的标签不可删除（它们是事实）；自述标签随时可以删，并始终标明「自述」。", sticker: "nameplate-blank.png")
            }
        }
        .omToast($toast)
    }
}

/// M3 · 信任等级详情（主路径：当前等级 + 下一级进度/条件 + 权益；完整标准进升级说明）
struct M3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "信任进度", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .homeReply, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t1("你在 T2 · 靠谱同学")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMTextRole.foot("比赛组队、自行发起和双人局已经打开")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, 4)

                OMSection(title: "升到下一级")
                OMCard {
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("T3 · 组局者")
                                .font(OMTheme.TypeToken.callout.weight(.bold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                            OMTextRole.foot("还差 2 项条件")
                        }
                        Spacer()
                        OMTextRole.monoFoot("46%")
                    }
                    OMProgressBar(value: 0.46)
                        .padding(.top, OMTheme.Spacing.s2)
                    progressRow(title: "有效成局", value: "7 / 10 次", ratio: 0.7, met: false)
                    progressRow(title: "本人发起并完成", value: "2 / 3 次", ratio: 0.66, met: false)
                    progressRow(title: "复局", value: "2 / 2 次", ratio: 1, met: true)
                    progressRow(title: "爽约率（越低越好）", value: "4% / 低于 10%", ratio: 1, met: true)
                }

                OMSection(title: "本级已解锁")
                OMCard {
                    benefitLine("进入比赛 / 项目组队池")
                    benefitLine("自行发起公开局")
                    benefitLine("参与双人局与跨院系匹配")
                    benefitLine("使用校园预约代理")
                }

                OMSection(title: "升到组局者将解锁")
                OMCard {
                    benefitLine("创建长期共同目标", muted: true)
                    benefitLine("发起周期性固定局 / 复局", muted: true)
                    benefitLine("组织 6 人以上的大组", muted: true)
                    benefitLine("使用补位快线", muted: true)
                }

                OMNote(text: "主路径只看「离下一级还差什么」。完整 T0–T4 达标标准见升级说明；不展示服务端能力键名。等级只解锁能力，别人看不到你的等级。", sticker: "access-card.png")
                OMButton("查看升级说明 · T0–T4 标准", kind: .ghost) { prototypeGo("M3", actions) }
                OMButton("对判定有异议？信任申诉 →", kind: .text) { prototypeGo("M9", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }

    private func progressRow(title: String, value: String, ratio: Double, met: Bool) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: met ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(met ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                Text(title)
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer()
                Text(value)
                    .font(OMTheme.TypeToken.mono(.caption, weight: .bold))
                    .foregroundStyle(met ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
            }
            OMProgressBar(value: ratio)
        }
        .padding(.top, OMTheme.Spacing.s3)
    }

    private func benefitLine(_ text: String, muted: Bool = false) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: muted ? "lock.open" : "sparkles")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(muted ? OMTheme.ColorToken.sage : OMTheme.ColorToken.ink)
            Text(text)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(muted ? OMTheme.ColorToken.mist : OMTheme.ColorToken.ink)
            Spacer(minLength: 0)
        }
        .padding(.top, 6)
    }
}

/// M4 · 授权管理
struct M4Screen: View {
    let actions: PrototypeActions
    @State private var timetable = true
    @State private var plan = true
    @State private var courseHistory = false
    @State private var agentExec = true

    var body: some View {
        PrototypePage(nav: "授权管理", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "books-stack.png", title: "课表", sub: "用于寻找空档 · 授权于 8 月 1 日", toggle: $timetable)
                    OMRow(sticker: "notebook-open.png", title: "培养方案", sub: "用于能力标签 · 授权于 8 月 1 日", toggle: $plan)
                    OMRow(sticker: "desk-calendar.png", title: "选课记录", sub: "未授权", toggle: $courseHistory)
                    OMRow(sticker: "approval-stamp.png", title: "代理执行", sub: "每次执行前仍需你确认 · 授权于 8 月 1 日", toggle: $agentExec)
                }
                OMNote(text: "撤回立即生效，且不删除历史：已经订好的场、写好的日历保持原样，只是以后不再代办。", sticker: "access-card.png")
            }
        }
    }
}

/// M5 · 隐私与安全
struct M5Screen: View {
    let actions: PrototypeActions
    @State private var social = true
    @State private var publicPlace = true
    @State private var before2200 = true

    var body: some View {
        PrototypePage(nav: "隐私与安全", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "chat-bubble.png", title: "社交能力", sub: "公开局 · 群聊 · 搭子关系", toggle: $social)
                    OMRow(icon: .pin, title: "默认公共场所", sub: "新局默认勾选", toggle: $publicPlace)
                    OMRow(icon: .clock, title: "局不晚于 22:00", sub: "新局默认勾选", toggle: $before2200)
                }
                OMSection(title: "永远关闭的")
                OMCard(tight: true) {
                    OMRow(icon: .shield, title: "双向确认前匿名", sub: "系统级规则，不可关闭") {
                        OMChip(text: "锁定", kind: .solid)
                    }
                    OMRow(icon: .shield, title: "已读回执 / 在线状态", sub: "产品不提供，不是设置项") {
                        OMChip(text: "不存在", kind: .solid)
                    }
                    OMRow(icon: .shield, title: "陌生人私聊", sub: "产品不提供，不是设置项") {
                        OMChip(text: "不存在", kind: .solid)
                    }
                }
            }
        }
    }
}

/// M6 · 匹配偏好
struct M6Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "匹配偏好", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "round-table.png", title: "局的规模", sub: "2–6 人") { OMChip(text: "可调") }
                    OMRow(icon: .pin, title: "校区范围", sub: "东校园优先 · 可接受南校园") { OMChip(text: "可调") }
                    OMRow(icon: .clock, title: "偏好时段", sub: "工作日晚 · 周末下午") { OMChip(text: "可调") }
                    OMRow(sticker: "hourglass.png", title: "招募时长", sub: "默认 48 小时") { OMChip(text: "可调") }
                }
                OMNote(text: "偏好只影响「推给你什么局」，不影响别人能不能看到你发起的局。", sticker: "chair-empty.png")
            }
        }
    }
}

/// M7 · 日历与通知
struct M7Screen: View {
    let actions: PrototypeActions
    @State private var ready = true
    @State private var pending = true
    @State private var scene = true
    @State private var calendar = true

    var body: some View {
        PrototypePage(nav: "通知与日历", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(icon: .bell, title: "凑齐提醒", sub: "局满员时推送", toggle: $ready)
                    OMRow(icon: .bell, title: "待确认提醒", sub: "有人等你表态时推送", toggle: $pending)
                    OMRow(icon: .bell, title: "场景建议", sub: "如「图书馆今晚空着」· 每天最多 1 条", toggle: $scene)
                    OMRow(sticker: "desk-calendar.png", title: "日历同步", sub: "成局后自动写入系统日历", toggle: $calendar)
                }
                OMNote(text: "没有「好友动态」类推送，没有红点养成。通知只在你需要行动时出现。", sticker: "alarm-clock.png")
            }
        }
    }
}

/// M8 · 黑名单
struct M8Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "黑名单", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMG5StateView(state: .empty)
                OMTextRole.foot("被拉黑的人不会再出现在你的任何局里。\n对方不会知道自己被拉黑。")
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
            }
        }
    }
}

/// M9 · 申诉
struct M9Screen: View {
    let actions: PrototypeActions
    @State private var detail = ""
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "信任申诉", back: true, backTarget: .m3, actions: actions) {
            OMButton("提交申诉") { toast = "已提交 · 复核结果会通知你（演示）" }
        } content: {
            VStack(spacing: 0) {
                OMCard {
                    OMTextRole.t3("对哪次判定有异议？")
                    OMTextRole.foot("申诉由真人复核，3 个工作日内回复").padding(.top, 4)
                    OMDivider()
                    OMRow(sticker: "table-tennis.png", title: "7 月 30 日 · 乒乓球双打", sub: "判定：临近开始退出 · 你认为：场馆临时关闭") {
                        OMChip(text: "可申诉", kind: .gap)
                    }
                }
                TextEditor(text: $detail)
                    .font(OMTheme.TypeToken.body)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .scrollContentBackground(.hidden)
                    .overlay(alignment: .topLeading) {
                        if detail.isEmpty {
                            Text("补充事实经过（可选）。复核只看事实记录，不看任何人的评价。")
                                .font(OMTheme.TypeToken.body)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                                .padding(.horizontal, OMTheme.Spacing.s4)
                                .padding(.vertical, OMTheme.Spacing.s3)
                                .allowsHitTesting(false)
                        }
                    }
                    .omInputStyle(multiline: true)
                    .padding(.top, OMTheme.Spacing.s3)
            }
        }
        .omToast($toast)
    }
}

/// M10 · 账号与数据
struct M10Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "账号与数据", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "envelope.png", title: "导出我的数据", sub: "画像 · 局记录 · 共同经历 · JSON 格式") {
                        Text("›").font(.system(size: 15, weight: .bold)).foregroundStyle(OMTheme.ColorToken.sage)
                    }
                    OMRow(sticker: "certificate.png", title: "界面状态规范", sub: "加载 / 空 / 错误等八种全局状态", onTap: { prototypeGo("G5", actions) })
                }
                OMCard(tight: true) {
                    OMRow(icon: .exit, title: "注销账号", sub: "删除全部数据 · 进行中的局会交接或解散") {
                        Text("›").font(.system(size: 15, weight: .bold)).foregroundStyle(OMTheme.ColorToken.sage)
                    }
                }
                OMNote(text: "注销前会逐项告诉你：哪些数据被删除、哪些已成局的事实记录会以匿名形式保留（场地预约凭证等学校要求的存根）。", sticker: "access-card.png")
            }
        }
    }
}
#endif
