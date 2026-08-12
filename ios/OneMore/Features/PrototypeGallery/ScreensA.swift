#if DEBUG
import SwiftUI

// MARK: - A · 认证与初始化（screens-1.js）

/// A1 · 启动路由
struct A1Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(actions: actions) {
            VStack(spacing: 0) {
                VStack(spacing: 0) {
                    LuluView(clip: .homeIdle, placement: .empty)
                    OMTextRole.t2(AppBrand.displayName).padding(.top, OMTheme.Spacing.s4)
                    OMTextRole.foot(AppBrand.slogan).padding(.top, 4)
                    OMProgressBar(value: 0.64)
                        .frame(width: 120)
                        .padding(.top, OMTheme.Spacing.s6)
                    OMTextRole.cap("正在检查登录状态…").padding(.top, OMTheme.Spacing.s3)
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 110)

                OMCard(tight: true) {
                    Text("冷启动路由：未登录 → ")
                        .font(OMTheme.TypeToken.footnote)
                    + Text("认证说明").font(OMTheme.TypeToken.footnote.weight(.bold))
                    + Text(" · 已登录 → ").font(OMTheme.TypeToken.footnote)
                    + Text("今天").font(OMTheme.TypeToken.footnote.weight(.bold))
                    + Text(" · 会话失效 → ").font(OMTheme.TypeToken.footnote)
                    + Text("认证恢复").font(OMTheme.TypeToken.footnote.weight(.bold))
                    HStack(spacing: 8) {
                        OMButton("未登录路径", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("A2", actions) }
                        OMButton("会话失效路径", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("G3", actions) }
                        OMButton("已登录路径", kind: .ghost, small: true, fillsWidth: false) { prototypeGo("tab:today", actions) }
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s4)
            }
        }
    }
}

/// A2 · 价值引导
struct A2Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(actions: actions) {
            VStack(spacing: 0) {
                OMButton("用企业微信扫码认证") { prototypeGo("A3", actions) }
                OMTextRole.cap("仅限中山大学师生 · 全程不输入密码")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .homeReply, placement: .hero)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s6)
                OMTextRole.hero("说一句想做的事，\n剩下的交给噜噜")
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.call("想找人打比赛、凑人打球、约研讨室赶 DDL——\n人凑齐、场订好，它就退场。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 290)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMRow(sticker: "round-table.png", title: "最小单位是「一个局」", sub: "没有人物卡片，没有刷人，没有加好友")
                    OMRow(sticker: "hourglass.png", title: "AI 越早退场越好", sub: "事办成就走，剩下的你们自己聊")
                    OMRow(sticker: "approval-stamp.png", title: "凑不齐就安静结束", sub: "没有人知道你开过口")
                }
                .padding(.top, OMTheme.Spacing.s6)
            }
        }
    }
}

/// A3 · 扫码认证
struct A3Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "扫码认证", back: true, backTarget: .a2, actions: actions) {
            OMButton("我已在企业微信完成扫码") { prototypeGo("A4", actions) }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .homeListening, placement: .header, caption: "打开企业微信，扫一扫")
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMQRBox { OMQRPattern() }
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.foot("企业微信 → 工作台 → 扫一扫\n认证只确认「你是中大人」，不读取聊天")
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s4)
                OMNote(text: "认证信息仅来自学校统一身份平台：姓名、学号、院系、年级。我们无法也不会修改。", sticker: "access-card.png")
                    .padding(.top, OMTheme.Spacing.s5)
            }
        }
    }
}

/// A4 · 授权范围
struct A4Screen: View {
    let actions: PrototypeActions
    @State private var timetable = true
    @State private var plan = true
    @State private var courseHistory = false
    @State private var agentExec = true

    var body: some View {
        PrototypePage(nav: "授权范围", back: true, backTarget: .a3,
                      large: "只给你愿意给的", largeSub: "每一项都可以单独关闭，之后随时改",
                      actions: actions) {
            OMButton("继续") { prototypeGo("A5", actions) }
        } content: {
            VStack(spacing: 0) {
                OMCard {
                    OMRow(sticker: "books-stack.png", title: "课表", sub: "用来找你的真实空档", toggle: $timetable)
                    OMRow(sticker: "notebook-open.png", title: "培养方案", sub: "生成能力标签的来源之一", toggle: $plan)
                    OMRow(sticker: "desk-calendar.png", title: "选课记录", sub: "辅助判断你上过哪些课", toggle: $courseHistory)
                    OMRow(sticker: "approval-stamp.png", title: "代理执行", sub: "订场、写日历前的最后一步确认权永远在你手里", toggle: $agentExec)
                }
                OMNote(text: "关闭某一项只会影响对应能力：例如关闭课表后，噜噜无法自动找空档，你仍可以手动选时间。", sticker: "nameplate-blank.png")
                OMButton("看看权限被拒绝时会怎样", kind: .text) { prototypeGo("A8", actions) }
                    .padding(.top, OMTheme.Spacing.s3)
            }
        }
    }
}

/// A5 · 画像初始化
struct A5Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "画像初始化", back: true, backTarget: .a4, actions: actions) {
            VStack(spacing: 0) {
                LuluView(clip: .homeThinking, placement: .hero, caption: "正在读你的课表和培养方案…")
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s6)
                OMCard {
                    OMTimeline(items: [
                        OMTimelineItem(state: .done, title: "统一身份认证", detail: "已确认 · 电子信息与工程学院 2023 级"),
                        OMTimelineItem(state: .done, title: "读取课表", detail: "本学期 6 门课 · 识别出 9 段固定空档"),
                        OMTimelineItem(state: .now, title: "生成能力标签", detail: "正在从培养方案与选课记录提取…"),
                        OMTimelineItem(state: .upcoming, title: "整理可用时间", detail: "稍后完成"),
                    ])
                }
                .padding(.top, OMTheme.Spacing.s6)
                OMTextRole.foot("不用填任何表。读完会给你确认。")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
            }
        }
    }
}

/// A6 · 画像确认
struct A6Screen: View {
    let actions: PrototypeActions

    var body: some View {
        PrototypePage(nav: "画像确认", back: true, backTarget: .a4,
                      large: "确认三件事", largeSub: "这是噜噜帮你组队时唯一依据的画像",
                      actions: actions) {
            OMButton("确认，继续") { prototypeGo("A7", actions) }
        } content: {
            VStack(spacing: 0) {
                OMSection(title: "认证事实 · 来自学校，不可改")
                OMCard(tight: true) {
                    OMRow(sticker: "teaching-building.png", title: "中山大学 · 东校园", sub: "电子信息和通信工程学院 · 2023 级本科")
                }
                OMSection(title: "能力标签 · 每个都有来源")
                OMCard(tight: true) {
                    OMRow(sticker: "algorithm-gear.png", title: "算法", sub: "来源：已修《数据结构与算法》92 分") {
                        OMChip(text: "课程", kind: .solid)
                    }
                    OMRow(sticker: "backend-server.png", title: "后端", sub: "来源：已修《操作系统》《数据库系统》") {
                        OMChip(text: "课程", kind: .solid)
                    }
                    OMRow(sticker: "design-palette.png", title: "设计", sub: "来源：你稍后可以自己加") {
                        OMChip(text: "自述")
                    }
                }
                OMSection(title: "可用时间 · 来自课表空档")
                OMCard(tight: true) {
                    OMFlowLayout {
                        OMChip(text: "周二 19:00–21:30", kind: .soft)
                        OMChip(text: "周三 14:00–17:00", kind: .soft)
                        OMChip(text: "周五 16:00 后", kind: .soft)
                        OMChip(text: "周末全天", kind: .soft)
                    }
                    OMTextRole.foot("只展示「什么时候有空」，不展示忙碌原因。")
                        .padding(.top, OMTheme.Spacing.s3)
                }
            }
        }
    }
}

/// A7 · 社交开关
struct A7Screen: View {
    let actions: PrototypeActions
    @State private var socialOn = false

    var body: some View {
        PrototypePage(nav: "社交开关", back: true, backTarget: .a6, actions: actions) {
            VStack(spacing: 0) {
                OMButton("先不开，进入 App", kind: .ghost) { prototypeGo("tab:today", actions) }
                OMButton("开启并进入") { prototypeGo("tab:today", actions) }
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } content: {
            VStack(spacing: 0) {
                LuluView(clip: .coreCare, placement: .header)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s6)
                OMTextRole.t1("社交能力，默认关闭")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s4)
                OMTextRole.call("打开后，你发起的局可以公开招募，成局后可以和队友聊天。\n不开，也能用全部校园工具。")
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 280)
                    .frame(maxWidth: .infinity)
                    .padding(.top, OMTheme.Spacing.s3)
                OMCard {
                    OMRow(sticker: "chat-bubble.png", title: "开启社交能力", sub: "公开局 · 局内群聊 · 搭子关系", toggle: $socialOn)
                }
                .padding(.top, OMTheme.Spacing.s6)
                OMNote(text: "即使开启：双向确认前对方看不到你的真实身份；没有陌生人私聊；没有已读回执和在线状态。", sticker: "access-card.png")
            }
        }
    }
}

/// A8 · 系统权限
struct A8Screen: View {
    let actions: PrototypeActions
    @State private var toast: String?

    var body: some View {
        PrototypePage(nav: "系统权限", back: true, backTarget: .a4, actions: actions) {
            OMButton("去系统设置开启") { toast = "已打开系统设置（演示）" }
        } content: {
            VStack(spacing: 0) {
                OMG5StateView(state: .permissionDenied)
                OMCard {
                    OMTextRole.t3("权限被拒后影响了什么").padding(.bottom, OMTheme.Spacing.s2)
                    OMRow(sticker: "desk-calendar.png", title: "日历写入：未开启", sub: "订场成功后无法自动写进日历，改为手动添加")
                    OMRow(sticker: "alarm-clock.png", title: "通知：未开启", sub: "凑齐、待确认不会推送，只在 App 内显示")
                }
                OMNote(text: "拒绝不会惩罚你：所有核心功能仍可用，只是少了自动化。恢复路径永远是这一页，不会藏在系统设置里让你找。", sticker: "chat-bubble.png")
            }
        }
        .omToast($toast)
    }
}
#endif
