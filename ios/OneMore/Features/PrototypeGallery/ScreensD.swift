#if DEBUG
import SwiftUI

// MARK: - D · 意图与匹配（screens-2.js）

/// D1 · 意图输入（Tab 根：差一个）
struct D1Screen: View {
    let actions: PrototypeActions
    @State private var intent = ""

    var body: some View {
        PrototypePage(tab: .create, actions: actions) {
            OMButton("说完了，交给噜噜") { prototypeGo("D2", actions) }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .homeListening, placement: .hero, caption: "我在听。说一句想做的事就行。")
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s5)

                VStack(spacing: 0) {
                    TextEditor(text: $intent)
                        .font(OMTheme.TypeToken.body)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .scrollContentBackground(.hidden)
                        .frame(minHeight: 96, alignment: .topLeading)
                        .overlay(alignment: .topLeading) {
                            if intent.isEmpty {
                                Text("例如：周五晚上想找人打半场篮球，缺两个后卫")
                                    .font(OMTheme.TypeToken.body)
                                    .foregroundStyle(OMTheme.ColorToken.mist)
                                    .allowsHitTesting(false)
                            }
                        }
                    HStack {
                        OMTextRole.cap("不用指定找谁")
                        Spacer()
                        OMIconButton(icon: .mic, accessibilityLabel: "语音输入") {}
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                .padding(OMTheme.Spacing.s4)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(OMTheme.ColorToken.card)
                .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.xLarge))
                .overlay {
                    RoundedRectangle(cornerRadius: OMTheme.Radius.xLarge)
                        .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                }
                .padding(.top, OMTheme.Spacing.s4)
                .padding(.bottom, OMTheme.Spacing.s3)

                OMFlowLayout {
                    OMChip(text: "明晚研讨室赶 DDL", kind: .soft, sticker: "books-stack.png")
                    OMChip(text: "数模缺一个写作的", kind: .soft, sticker: "trophy.png")
                    OMChip(text: "周末羽毛球双打", kind: .soft, sticker: "badminton.png")
                }
                .frame(maxWidth: .infinity)
                .padding(.top, OMTheme.Spacing.s4)
            }
        }
    }
}

/// D2 · 澄清追问
struct D2Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "澄清一下", back: true, backTarget: .d1, actions: actions) {
            OMButton("不限，能跑就行") { prototypeGo("D3", actions) }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .homeThinking, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                VStack(spacing: 10) {
                    OMChatBubble("周五晚上想找人打半场篮球，缺两个后卫", mine: true)
                    OMChatBubble("明白。确认两件事：\n1. 时间定在 周五 19:00–21:00 可以吗？那是你和场馆都空着的时段。", mine: false)
                    OMChatBubble("可以", mine: true)
                    OMChatBubble("2. 水平有要求吗？比如「打过全场就行」，还是不限？", mine: false)
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMFlowLayout {
                    OMChip(text: "不限，能跑就行", kind: .soft)
                    OMChip(text: "打过全场", kind: .soft)
                    OMChip(text: "院队水平", kind: .soft)
                }
                .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.cap("最多问两轮，问完就出意图卡")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// D3 · 意图卡确认
struct D3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "意图卡确认", back: true, backTarget: .d2, actions: actions) {
            VStack(spacing: 0) {
                OMButton("确认，开始招募") { prototypeGo("D4", actions) }
                OMButton("改需要的能力", kind: .text) { prototypeGo("D3.1", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .intentCard, placement: .confirm)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMTextRole.t2("我理解对了吗？")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
                OMCard(borderColor: OMTheme.ColorToken.yolk, borderWidth: 2) {
                    OMRow(sticker: "basketball.png", title: "做什么", sub: "篮球半场 4v4", onTap: { prototypeGo("D3.3", actions) })
                    OMRow(icon: .clock, title: "什么时候", sub: "周五 19:00–21:00", onTap: { prototypeGo("D3.2", actions) })
                    OMRow(sticker: "round-table.png", title: "需要几个人", sub: "连你共 4 人", onTap: { prototypeGo("D3.3", actions) })
                    OMRow(sticker: "basketball.png", title: "角色缺口", sub: "后卫 × 2 · 水平不限", onTap: { prototypeGo("D3.3", actions) })
                    OMRow(icon: .shield, title: "安全偏好", sub: "公共场所 · 默认", onTap: { prototypeGo("D3.4", actions) })
                }
                .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "确认后进入匿名招募。满员前，没有人知道你是谁。", sticker: "access-card.png")
            }
        }
    }
}

/// D3.1 · 能力标签编辑
struct D31Screen: View {
    let actions: PrototypeActions
    @State private var flags = [false, false, false, false, false, false]
    private let tags: [(sticker: String, title: String, sub: String)] = [
        ("algorithm-gear.png", "算法", "建模、题解、复杂度"),
        ("backend-server.png", "后端", "服务、数据库、部署"),
        ("frontend-browser.png", "前端", "界面、交互、小程序"),
        ("data-chart.png", "数据", "分析、可视化、建模"),
        ("product-notes.png", "产品", "需求、文档、路演"),
        ("design-palette.png", "设计", "视觉、海报、PPT"),
    ]

    var body: some View {
        PrototypePage(nav: "能力编辑", back: true, backTarget: .d3, actions: actions) {
            OMButton("保存") { prototypeGo("D3", actions) }
        } content: {
            VStack(spacing: 0) {
                OMTextRole.foot("给这个局标注需要的能力。标签只描述「这件事需要什么」，不描述人。")
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    ForEach(Array(tags.enumerated()), id: \.offset) { index, tag in
                        OMRow(sticker: tag.sticker, title: tag.title, sub: tag.sub, toggle: $flags[index])
                    }
                }
            }
        }
    }
}

/// D3.2 · 空档选择器
struct D32Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "空档选择", back: true, backTarget: .d3, actions: actions) {
            OMButton("就用周五晚上") { prototypeGo("D3", actions) }
        } content: {
            VStack(spacing: 0) {
                OMTextRole.foot("黄色格是你的固定空档。只能在这些时间里选——这是「不打扰」的边界。")
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMCard(tight: true) {
                    OMScheduleGrid(rows: [
                        [.init(.head), .init(.head, "三"), .init(.head, "四"), .init(.head, "五"), .init(.head, "六"), .init(.head, "日")],
                        [.init(.time, "下午"), .init(.empty), .init(.free, "空档"), .init(.free, "空档"), .init(.free, "空档"), .init(.free, "空档")],
                        [.init(.time, "晚上"), .init(.empty), .init(.empty), .init(.free, "已选 19–21", selected: true), .init(.free, "空档"), .init(.free, "空档")],
                    ])
                }
                OMCard(tight: true) {
                    OMRow(icon: .clock, title: "周五 19:00–21:00", sub: "与场馆空闲重合") {
                        OMChip(text: "当前选择", kind: .gap)
                    }
                    OMRow(icon: .clock, title: "周六 15:00–17:00", sub: "场馆需现场确认") {
                        OMButton("换这个", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("D3", actions) }
                    }
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// D3.3 · 角色需求编辑
struct D33Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "角色编辑", back: true, backTarget: .d3, actions: actions) {
            OMButton("保存席位") { prototypeGo("D3", actions) }
        } content: {
            VStack(spacing: 0) {
                OMTextRole.foot("一个局最少 2 人、最多 12 人。每个席位写清角色，别人才知道自己补的是哪。")
                    .padding(.bottom, OMTheme.Spacing.s3)
                OMSeatTable(name: "篮球 4v4 · 席位", seats: [
                    OMSeat(role: "你 · 前锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "中锋", state: .filled, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                    OMSeat(role: "后卫", state: .gap, sticker: "basketball.png"),
                ], tableSticker: "basketball.png")
                HStack(spacing: 8) {
                    OMButton("加一个席位", kind: .ghost, small: true) { toast = "已加到 5 席（演示）" }
                    OMButton("减一个席位", kind: .ghost, small: true) { toast = "至少保留 2 席" }
                }
                .padding(.top, OMTheme.Spacing.s2)
            }
        }
        .omToast($toast)
    }
}

/// D3.4 · 社交模式与安全偏好
struct D34Screen: View {
    let actions: PrototypeActions
    @State private var publicPlace = true
    @State private var sameGender = false
    @State private var before2200 = true

    var body: some View {
        PrototypePage(nav: "安全偏好", back: true, backTarget: .d3, actions: actions) {
            OMButton("保存") { prototypeGo("D3", actions) }
        } content: {
            VStack(spacing: 0) {
                OMCard(tight: true) {
                    OMRow(icon: .pin, title: "只在公共场所进行", sub: "体育馆、图书馆、教学楼等学校场地", toggle: $publicPlace)
                    OMRow(sticker: "access-card.png", title: "同性别组队", sub: "仅对运动类局生效", toggle: $sameGender)
                    OMRow(icon: .clock, title: "不晚于 22:00 结束", sub: "宿舍门禁前留出路程", toggle: $before2200)
                    OMRow(icon: .shield, title: "双向确认前匿名", sub: "系统默认，不可关闭") {
                        OMChip(text: "锁定", kind: .solid)
                    }
                }
                OMNote(text: "安全偏好会写进局卡，加入的人在确认前就能看到并遵守。", sticker: "access-card.png")
            }
        }
    }
}

/// D4 · 招募中（匿名池）
struct D4Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "匿名池", back: true, backTarget: .b1, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .poolWaiting, placement: .hero)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.t1("正在匿名招募")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s3)
                OMGapHero(2, suffix: "个后卫位还空着")
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    HStack {
                        OMTextRole.foot("招募剩余时间")
                        Spacer()
                        Text("41:22:08").font(OMTheme.TypeToken.mono(.headline, weight: .bold))
                    }
                    .padding(.bottom, OMTheme.Spacing.s2)
                    OMProgressBar(value: 0.38)
                    OMDivider()
                    OMRow(icon: .shield, title: "全程匿名", sub: "满员前，没有人知道你是谁，你也不知道有谁")
                    OMRow(sticker: "hourglass.png", title: "周五 12:00 截止", sub: "到点未满员，这个局会安静解散，不归因给任何人")
                }
                .padding(.top, OMTheme.Spacing.s5)
                HStack(spacing: 8) {
                    OMButton("分享缺口卡到微信群", kind: .ghost) { prototypeGo("G2", actions) }
                    OMButton("取消招募", kind: .text, fillsWidth: false) { prototypeGo("E12", actions) }
                }
            }
        }
    }
}
#endif
