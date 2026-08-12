#if DEBUG
import SwiftUI

// MARK: - C · 公开局与站外落地（screens-2.js）

/// C1 · 公开局
struct C1Screen: View {
    let actions: PrototypeActions
    @State private var seg = "全部"

    var body: some View {
        PrototypePage(nav: "公开局", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                OMSeg(items: ["全部", "运动", "学业", "比赛"], label: { $0 }, selection: $seg)
                    .padding(.bottom, OMTheme.Spacing.s3)

                OMCard {
                    HStack {
                        HStack(spacing: 10) {
                            OMSticker("basketball.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3("周五晚篮球半场 4v4")
                                OMTextRole.foot("周五 19:00 · 东校园室外场")
                            }
                        }
                        Spacer()
                        OMGapBadge(count: 2)
                    }
                    HStack {
                        OMSeatStrip(seats: [
                            OMSeat(role: "前锋", state: .filled, sticker: "basketball.png"),
                            OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                            OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                            OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                        ])
                        Spacer()
                        OMTextRole.foot("匿名招募中")
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .omCardTap("C2", actions)

                OMCard {
                    HStack {
                        HStack(spacing: 10) {
                            OMSticker("books-stack.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3("操作系统考前冲刺")
                                OMTextRole.foot("周四 19:00 · 图书馆研讨间")
                            }
                        }
                        Spacer()
                        OMGapBadge(count: 1)
                    }
                    HStack {
                        OMSeatStrip(seats: [
                            OMSeat(role: "串讲", state: .filled, sticker: "books-stack.png"),
                            OMSeat(role: "刷题", state: .filled, sticker: "notebook-open.png"),
                            OMSeat(role: "答疑", state: .gap, sticker: "chat-bubble.png"),
                        ])
                        Spacer()
                        OMTextRole.foot("匿名招募中")
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .omCardTap("C2", actions)

                OMCard {
                    HStack {
                        HStack(spacing: 10) {
                            OMSticker("trophy.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3("挑战杯 · 智能硬件方向")
                                OMTextRole.foot("赛季局 · 10 月校赛")
                            }
                        }
                        Spacer()
                        OMChip(text: "有准入门槛")
                    }
                    OMTextRole.foot("需要 T2 及以上 · 看看怎么达到 →")
                        .padding(.top, OMTheme.Spacing.s2)
                }
                .omCardTap("C3", actions)

                OMNote(text: "这里只显示角色缺口与人数进度。不显示成员是谁，也不显示任何人的信任等级。", sticker: "access-card.png")
            }
        }
    }
}

/// C2 · 公开局详情
struct C2Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "公开局详情", back: true, backTarget: .c1, actions: actions) {
            VStack(spacing: 0) {
                OMButton("补一个「后卫」位") { prototypeGo("D4", actions) }
                OMButton("分享给微信同学", kind: .ghost) { prototypeGo("G2", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                OMSeatTable(name: "周五晚篮球 4v4", seats: [
                    OMSeat(role: "前锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                ], tableSticker: "basketball.png")

                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "周五 19:00–21:00", sub: "东校园室外篮球场 3 号场")
                    OMRow(icon: .shield, title: "安全偏好", sub: "公共场所 · 双向确认后才可见身份")
                    OMRow(sticker: "hourglass.png", title: "招募截止", sub: "周五 12:00 · 未满员则安静解散")
                }
                OMNote(text: "加入后你的身份对其他成员保持匿名，直到双方都确认成局。", sticker: "access-card.png")
            }
        }
    }
}

/// C3 · 准入门槛说明
struct C3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "准入门槛", back: true, backTarget: .c1, actions: actions) {
            OMButton("去看看我能进的局") { prototypeGo("C1", actions) }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("这个局暂时进不去")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.call("不是拒绝你——是这个局设了门槛，而你还差一步。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard {
                    OMTextRole.t3("「挑战杯 · 智能硬件」要求").padding(.bottom, OMTheme.Spacing.s2)
                    OMRow(sticker: "approval-stamp.png", title: "信任等级 T2", sub: "你当前 T1 · 完成 1 次成局即可升到 T2") {
                        OMChip(text: "差 1 次成局", kind: .gap)
                    }
                    OMRow(sticker: "algorithm-gear.png", title: "至少 1 个相关能力标签", sub: "你已有「算法」· 已满足") {
                        OMChip(text: "已满足", kind: .solid)
                    }
                }
                .padding(.top, OMTheme.Spacing.s5)
                OMTextRole.call("先去打成任何一个局，回来这扇门就开了。")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
    }
}

/// C4 · 缺口卡落地页（站外，无导航）
struct C4Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(actions: actions) {
            VStack(spacing: 0) {
                OMButton("企业微信扫码认证") { prototypeGo("A3", actions) }
                OMTextRole.cap("中山大学师生专属 · 认证后回到本局")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                OMSticker("qr-plaque-blank.png", size: .s96)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s6)
                OMTextRole.t1("有人差一个你")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.call("这是一张来自「噜噜成局」的缺口卡")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard {
                    HStack {
                        HStack(spacing: 10) {
                            OMSticker("basketball.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3("周五晚篮球半场 4v4")
                                OMTextRole.foot("周五 19:00 · 东校园室外场")
                            }
                        }
                        Spacer()
                        OMGapBadge(count: 2)
                    }
                    OMSeatStrip(seats: [
                        OMSeat(role: "前锋", state: .filled, sticker: "basketball.png"),
                        OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                        OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                        OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                    ])
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .padding(.top, OMTheme.Spacing.s5)
                OMNote(text: "你还没有登录。认证后会直接回到这个局，不用重新找链接。", sticker: "access-card.png")
            }
        }
    }
}
#endif
