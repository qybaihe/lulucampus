#if DEBUG
import SwiftUI

// MARK: - O · 主理人 + G · 全局与跨阶段 + B12.2 组合态（screens-3.js）

/// O1 · 管理台首页
struct O1Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "主理人控制台", back: true, backTarget: .m1, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    HStack {
                        HStack(spacing: 10) {
                            OMSticker("certificate.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3("羽毛球协会 · 周五夜场")
                                OMTextRole.foot("官方局 · 每周五 19:00")
                            }
                        }
                        Spacer()
                        OMChip(text: "进行中", kind: .solid)
                    }
                    HStack {
                        OMSeatStrip(seats: [
                            OMSeat(role: "场 1", state: .filled, sticker: "badminton.png"),
                            OMSeat(role: "场 2", state: .filled, sticker: "badminton.png"),
                            OMSeat(role: "场 3", state: .gap, sticker: "badminton.png"),
                            OMSeat(role: "场 4", state: .gap, sticker: "badminton.png"),
                        ])
                        Spacer()
                        OMGapBadge(count: 2, label: "本周缺")
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                    HStack(spacing: 8) {
                        OMButton("报名看板", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("O3", actions) }
                        OMButton("分享缺口卡", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("G2", actions) }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                OMButton("创建官方局") { prototypeGo("O2", actions) }
                OMButton("从模板复用", kind: .ghost) { prototypeGo("O4", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }
}

/// O2 · 创建官方局
struct O2Screen: View {
    let actions: PrototypeActions
    @State private var name = "羽毛球协会 · 周五夜场"
    @State private var timePlace = "每周五 19:00–21:00 · 体育馆 2F"

    var body: some View {
        PrototypePage(nav: "创建官方局", back: true, backTarget: .o1, actions: actions) {
            OMButton("发布官方局") { prototypeGo("O3", actions) }
        } content: {
            VStack(spacing: 0) {
                OMCard {
                    OMTextRole.foot("局名称").padding(.bottom, OMTheme.Spacing.s2)
                    TextField("局名称", text: $name)
                        .omInputStyle()
                    OMTextRole.foot("时间与地点").padding(.bottom, OMTheme.Spacing.s2).padding(.top, OMTheme.Spacing.s4)
                    TextField("时间与地点", text: $timePlace)
                        .omInputStyle()
                    OMTextRole.foot("席位与角色").padding(.bottom, OMTheme.Spacing.s2).padding(.top, OMTheme.Spacing.s4)
                    OMFlowLayout {
                        OMChip(text: "场 1 · 双打 ×4", kind: .solid)
                        OMChip(text: "场 2 · 双打 ×4", kind: .solid)
                        OMChip(text: "场 3 · 双打 ×4", kind: .gap)
                        OMChip(text: "场 4 · 双打 ×4", kind: .gap)
                    }
                    OMTextRole.foot("官方标识").padding(.bottom, OMTheme.Spacing.s2).padding(.top, OMTheme.Spacing.s4)
                    OMRow(sticker: "approval-stamp.png", title: "显示「官方局」标", sub: "需社团指导教师确认 · 已确认") {
                        OMChip(text: "已核验", kind: .solid)
                    }
                }
                OMNote(text: "官方局同样遵守匿名招募规则：满员前你也看不到报名者是谁。", sticker: "access-card.png")
            }
        }
    }
}

/// O3 · 报名与到场看板
struct O3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "报名与到场看板", back: true, backTarget: .o1, actions: actions) {
            VStack(spacing: 0) {
                OMCard {
                    OMTextRole.t3("本周五 · 8 月 15 日")
                    OMGapHero(14, suffix: "/ 16 席已确认").padding(.top, OMTheme.Spacing.s3)
                    OMProgressBar(value: 0.87).padding(.top, OMTheme.Spacing.s3)
                    OMTextRole.foot("满员前不显示报名者身份 · 仅按席位统计").padding(.top, OMTheme.Spacing.s2)
                }
                OMCard(tight: true) {
                    OMRow(sticker: "badminton.png", title: "场 1 · 双打", sub: "4 / 4 · 已满") { OMChip(text: "满", kind: .solid) }
                    OMRow(sticker: "badminton.png", title: "场 2 · 双打", sub: "4 / 4 · 已满") { OMChip(text: "满", kind: .solid) }
                    OMRow(sticker: "badminton.png", title: "场 3 · 双打", sub: "3 / 4") { OMChip(text: "缺 1", kind: .gap) }
                    OMRow(sticker: "badminton.png", title: "场 4 · 双打", sub: "3 / 4") { OMChip(text: "缺 1", kind: .gap) }
                }
                OMSection(title: "到场核验（开场后）")
                OMCard(tight: true) {
                    OMRow(sticker: "qr-plaque-blank.png", title: "扫码到场", sub: "成员到场扫场地码 · 只记录「到了 / 没到」") {
                        OMChip(text: "周五启用")
                    }
                }
            }
        }
    }
}

/// O4 · 局模板
struct O4Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "官方局模板", back: true, backTarget: .o1, actions: actions) {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(sticker: "badminton.png", title: "周五夜场 · 4 片场", sub: "使用 12 次 · 最近：8 月 8 日") {
                        OMButton("复用", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("O2", actions) }
                    }
                    OMRow(sticker: "trophy.png", title: "新生杯 · 选拔赛", sub: "使用 2 次 · 最近：5 月 17 日") {
                        OMButton("复用", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("O2", actions) }
                    }
                    OMRow(sticker: "poster-blank.png", title: "协会招新体验场", sub: "使用 1 次 · 最近：3 月 2 日") {
                        OMButton("复用", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("O2", actions) }
                    }
                }
                OMNote(text: "模板保存的是局的结构（时间、地点、席位、规则），不保存任何参与者信息。", sticker: "certificate.png")
            }
        }
    }
}

// MARK: - G · 全局与跨阶段

/// G1 · hermes 唤起浮层（底部 sheet，下层页面保持不动）
struct G1Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(
            sheet: AnyView(sheetContent),
            actions: actions
        ) {
            VStack(spacing: 0) {
                OMSection(title: "下方页面保持不动")
                OMCard {
                    OMRow(sticker: "books-stack.png", title: "\(AppBrand.agentName) 以浮层唤起", sub: "不打断当前页面，关掉就回到原处")
                }
            }
            .opacity(0.35)
            .allowsHitTesting(false)
        }
    }

    private var sheetContent: some View {
        OMSheet {
            VStack(spacing: 0) {
                LuluView(clip: .homeListening, placement: .confirm)
                    .frame(maxWidth: .infinity)
                OMTextRole.t3(AppBrand.agentName)
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                VStack(spacing: 10) {
                    OMChatBubble("今晚图书馆哪层还有研讨间？", mine: true)
                    OMChatBubble("4 楼研讨间 4C 今晚 19:00–21:30 空闲，正好覆盖你的空档。要看预约预览吗？", mine: false)
                }
                .padding(.top, OMTheme.Spacing.s3)
                HStack(spacing: 8) {
                    TextField("继续问…", text: .constant(""))
                        .font(OMTheme.TypeToken.callout)
                        .padding(.horizontal, OMTheme.Spacing.s4)
                        .frame(minHeight: 44)
                        .background(OMTheme.ColorToken.paper)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
                        .overlay {
                            RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                    OMIconButton(icon: .mic, size: 44, accessibilityLabel: "语音") {}
                }
                .padding(.top, OMTheme.Spacing.s3)
                HStack(spacing: 8) {
                    OMButton("看预约预览", small: true) { prototypeGo("B11", actions) }
                    OMButton("关闭", kind: .text, small: true, fillsWidth: false) { actions.perform(.back) }
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// G2 · 缺口卡分享 Sheet
struct G2Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    /// 缺口数字用 AttributedString 上蛋黄底色（Text 拼接不支持 .background 视图）
    private static var gapCardHeadline: AttributedString {
        var text = AttributedString("周五晚篮球 4v4\n还差 ")
        var gap = AttributedString(" 2 ")
        gap.font = .system(size: 26, weight: .heavy, design: .monospaced)
        gap.foregroundColor = OMTheme.ColorToken.ink
        gap.backgroundColor = OMTheme.ColorToken.yolk
        text.append(gap)
        text.append(AttributedString(" 个后卫"))
        return text
    }

    var body: some View {
        PrototypePage(nav: "缺口卡分享", back: true, actions: actions) {
            VStack(spacing: 0) {
                OMButton("发到微信群") { toast = "已生成图片（演示）" }
                OMButton("复制链接", kind: .ghost) { toast = "链接已复制（演示）" }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                // 缺口卡：墨底卡头 + 卡身席位条
                VStack(spacing: 0) {
                    VStack(alignment: .leading, spacing: 0) {
                        HStack {
                            Text("\(AppBrand.displayName) · \(AppBrand.coreAction)")
                                .font(.system(size: 11, design: .monospaced))
                                .tracking(1.5)
                            Spacer()
                            Text("中山大学")
                                .font(.system(size: 11))
                                .foregroundStyle(OMTheme.ColorToken.sage)
                        }
                        Text(Self.gapCardHeadline)
                            .font(.system(size: 26, weight: .heavy))
                            .lineSpacing(4)
                            .padding(.top, OMTheme.Spacing.s4)
                        Text("周五 19:00 · 东校园室外场 3 号场")
                            .font(.system(size: 13))
                            .foregroundStyle(OMTheme.ColorToken.sage)
                            .padding(.top, OMTheme.Spacing.s3)
                    }
                    .foregroundStyle(OMTheme.ColorToken.paper)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 24)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(OMTheme.ColorToken.ink)

                    HStack {
                        OMSeatStrip(seats: [
                            OMSeat(role: "前锋", state: .filled, sticker: "basketball.png"),
                            OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                            OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                            OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                        ])
                        Spacer()
                        OMTextRole.cap("长按识别小程序码加入")
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                    .background(OMTheme.ColorToken.card)
                }
                .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.large))
                .overlay {
                    RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                        .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                }
                .padding(.top, OMTheme.Spacing.s3)
                .padding(.bottom, OMTheme.Spacing.s3)

                OMNote(text: "缺口卡只含：什么事、什么时候、缺什么角色。不含发起人身份，点进来的人先认证再看局。", sticker: "qr-plaque-blank.png")
            }
        }
        .omToast($toast)
    }
}

/// G3 · 重新扫码授权浮层（会话失效恢复）
struct G3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(actions: actions) {
            VStack(spacing: 0) {
                OMButton("已完成扫码，回到刚才的局") { prototypeGo("C2", actions) }
                OMTextRole.cap("恢复后回到：公开局详情 · 周五晚篮球")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .empty)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s6)
                OMTextRole.t1("登录状态失效了")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s4)
                (Text("出于安全考虑需要重新认证。\n扫一下就好——") + Text("你刚才在看的局会原地等你").bold())
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .lineSpacing(3)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 280)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s2)
                OMQRBox { OMQRPattern() }
                    .padding(.top, OMTheme.Spacing.s5)
            }
        }
    }
}

/// G4 · 静默解散处理
struct G4Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "已结束", back: true, backTarget: .e1, actions: actions) {
            VStack(spacing: 0) {
                OMButton("换个时间再试一次") { prototypeGo("D1", actions) }
                OMButton("好的", kind: .text) { prototypeGo("E1", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .exitBow, placement: .empty)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s5)
                OMTextRole.t1("这个局安静地结束了")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.call("「上周乒乓球双打」到截止时间没有凑齐。\n没有人被拒绝，也没有人知道你开过口。\n它就这样结束了，像没发生过一样。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 290)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMRow(sticker: "hourglass.png", title: "记录", sub: "只在你的「已结束」里保留 30 天，之后彻底删除")
                    OMRow(icon: .shield, title: "其他人看到的", sub: "什么都没有。没有通知，没有归因")
                }
                .padding(.top, OMTheme.Spacing.s6)
            }
        }
    }
}

/// G5 · 空 / 错 / 加载态规范（八种全局状态陈列）
struct G5Screen: View {
    let actions: PrototypeActions

    private let states: [(String, OMG5State)] = [
        ("1 · 加载", .loading),
        ("2 · 空", .empty),
        ("3 · 网络错误", .networkError),
        ("4 · 离线", .offline),
        ("5 · 权限拒绝", .permissionDenied),
        ("6 · 会话失效", .sessionExpired),
        ("7 · 重复点击", .duplicateTap),
        ("8 · 数据过期", .staleState),
    ]

    var body: some View {
        PrototypePage(nav: "状态规范", back: true, backTarget: .m10,
                      large: "八种全局状态", largeSub: "一套系统，所有页面共用 · 不各写各的",
                      actions: actions) {
            VStack(spacing: 0) {
                ForEach(states, id: \.0) { label, state in
                    OMSection(title: label)
                    OMCard {
                        OMG5StateView(state: state)
                    }
                }
                OMNote(text: "统一规则：噜噜在异常态永远用「关切」或「在想」；文案先说影响、再给动作；动作按钮最多一个主按钮。红色不出现在任何状态里。", sticker: "chat-bubble.png")
            }
        }
    }
}

// MARK: - B12.2 · 牌桌组合态（iOS 保留，新设计语言重述）

struct B122Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "牌桌 · 差一个", back: true, actions: actions) {
            OMButton("上桌 · 这桌差一个") { prototypeGo("D4", actions) }
        } content: {
            VStack(spacing: 0) {
                OMSeatTable(name: "周五晚篮球 4v4 · 差一个", seats: [
                    OMSeat(role: "前锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                ], tableSticker: "basketball.png")
                OMNote(text: "席位只显示角色缺口，不显示已就位者是谁。", sticker: "approval-stamp.png")
            }
        }
    }
}
#endif
