#if DEBUG
import SwiftUI

/// 原型屏壳，逐件对应 mobile-ios.html 的 .screen 结构：
/// om-nav（可选）→ om-large-title（可选）→ .scroll → om-footer（贴合内容，
/// 位于 tabbar 上方）→ om-sheet（可选）→ tabbar（仅主 Tab 屏）。
struct PrototypePage<Content: View>: View {
    var navTitle: String? = nil
    var showsBack = false
    /// 设计稿指定的返回目标（P.nav back:"X" / "tab:Y"）；nil = 弹出栈顶
    var backTarget: PrototypeScreenID? = nil
    var navRight: AnyView? = nil
    var large: String? = nil
    var largeSub: String? = nil
    var tab: OMTab? = nil
    var hasMessage = false
    var footer: AnyView? = nil
    var sheet: AnyView? = nil
    let actions: PrototypeActions
    let content: Content

    init(
        nav: String? = nil,
        back: Bool = false,
        backTarget: PrototypeScreenID? = nil,
        navRight: AnyView? = nil,
        large: String? = nil,
        largeSub: String? = nil,
        tab: OMTab? = nil,
        hasMessage: Bool = false,
        sheet: AnyView? = nil,
        actions: PrototypeActions,
        @ViewBuilder content: () -> Content
    ) {
        self.navTitle = nav
        self.showsBack = back
        self.backTarget = backTarget
        self.navRight = navRight
        self.large = large
        self.largeSub = largeSub
        self.tab = tab
        self.hasMessage = hasMessage
        self.actions = actions
        self.footer = nil
        self.sheet = sheet
        self.content = content()
    }

    init<Footer: View>(
        nav: String? = nil,
        back: Bool = false,
        backTarget: PrototypeScreenID? = nil,
        navRight: AnyView? = nil,
        large: String? = nil,
        largeSub: String? = nil,
        tab: OMTab? = nil,
        hasMessage: Bool = false,
        sheet: AnyView? = nil,
        actions: PrototypeActions,
        @ViewBuilder footer: () -> Footer,
        @ViewBuilder content: () -> Content
    ) {
        self.navTitle = nav
        self.showsBack = back
        self.backTarget = backTarget
        self.navRight = navRight
        self.large = large
        self.largeSub = largeSub
        self.tab = tab
        self.hasMessage = hasMessage
        self.actions = actions
        self.footer = AnyView(footer())
        self.sheet = sheet
        self.content = content()
    }

    var body: some View {
        ZStack(alignment: .bottom) {
            OMPageBackground()
            VStack(spacing: 0) {
                if let navTitle {
                    OMNavBar(
                        title: navTitle,
                        onBack: showsBack ? { onBack() } : nil,
                        trailing: navRight
                    )
                }
                if let large {
                    OMLargeTitle(title: large, sub: largeSub)
                }
                ScrollView(showsIndicators: false) {
                    content
                        .padding(.horizontal, OMTheme.Spacing.pageX)
                        .padding(.bottom, 120)
                }
            }

            // 底部动作区：贴合内容，位于 tabbar 上方（.om-footer）
            if let footer {
                VStack(spacing: 0) {
                    Spacer()
                    VStack(spacing: 0) { footer }
                        .padding(.horizontal, OMTheme.Spacing.pageX)
                        .padding(.top, 12)
                        .padding(.bottom, 14)
                        .background {
                            LinearGradient(
                                colors: [OMTheme.ColorToken.paper.opacity(0), OMTheme.ColorToken.paper],
                                startPoint: .top,
                                endPoint: .init(x: 0.5, y: 0.3)
                            )
                        }
                        .accessibilityIdentifier("prototype-bottom-action")
                    if tab == nil { Color.clear.frame(height: 20) }
                }
            }

            // 底部弹层 / 输入条：原始内容钉在底部，需要 .om-sheet 外观的屏自己包 OMSheet
            if let sheet {
                VStack {
                    Spacer()
                    sheet
                }
                .transition(.move(edge: .bottom))
                .zIndex(1)
            }

            if let tab {
                VStack {
                    Spacer()
                    OMTabBar(selected: tab, onSelect: routeTab, hasMessage: hasMessage)
                }
            }
        }
        .foregroundStyle(OMTheme.ColorToken.ink)
        .tint(OMTheme.ColorToken.ink)
        .preferredColorScheme(.light)
    }

    private func onBack() {
        if let backTarget {
            actions.route(backTarget)
        } else {
            actions.perform(.back)
        }
    }

    private func routeTab(_ tab: OMTab) {
        switch tab {
        case .today: actions.route(.b1)
        case .match: actions.route(.b12)
        case .create: actions.route(.d1)
        case .msg: actions.route(.msg)
        case .me: actions.route(.m1)
        }
    }
}

/// 键值行（详情页参数罗列）
struct PrototypeKeyValueRow: View {
    let key: String
    let value: String
    var valueColor = OMTheme.ColorToken.ink

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Text(key)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .frame(width: 70, alignment: .leading)
            Text(value)
                .font(OMTheme.TypeToken.body)
                .foregroundStyle(valueColor)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.vertical, 6)
    }
}

/// 设置开关行（.om-row + .om-switch）
struct PrototypeToggleRow: View {
    let title: String
    let detail: String
    @Binding var isOn: Bool

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 5) {
                Text(title).font(OMTheme.TypeToken.callout.weight(.semibold))
                Text(detail)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .lineSpacing(3)
            }
            Spacer()
            OMSwitch(isOn: $isOn)
        }
        .padding(.vertical, 13)
        .frame(minHeight: 48)
    }
}
#endif
