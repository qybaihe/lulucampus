import SwiftUI

/// 设计稿 app.js 的线性图标 → SF Symbols 映射（1.7 描边风格用 .regular 权重近似）。
enum OMIcon: String {
    case sun, trophy, plus, chat, person, back, bell, clock, pin, cal
    case shield, spark, arrow, share, flag, doc, gear, mic, scan, exit, warn, check

    var systemName: String {
        switch self {
        case .sun: "sun.max"
        case .trophy: "trophy"
        case .plus: "plus"
        case .chat: "bubble.left"
        case .person: "person"
        case .back: "chevron.left"
        case .bell: "bell"
        case .clock: "clock"
        case .pin: "mappin"
        case .cal: "calendar"
        case .shield: "checkmark.shield"
        case .spark: "sparkles"
        case .arrow: "arrow.right"
        case .share: "square.and.arrow.up"
        case .flag: "flag"
        case .doc: "doc.text"
        case .gear: "gearshape"
        case .mic: "mic"
        case .scan: "qrcode.viewfinder"
        case .exit: "rectangle.portrait.and.arrow.right"
        case .warn: "exclamationmark.triangle"
        case .check: "checkmark"
        }
    }
}

extension Image {
    init(om icon: OMIcon) { self.init(systemName: icon.systemName) }
}

// MARK: - 按钮（.om-btn：主行动 = 明黄底墨字；次级 = 墨描边；三级 = 纯文字）

enum OMButtonKind {
    /// yolk 底 + ink 字 + ink16/yolk 描边 —— 全屏最高视觉权重
    case primary
    /// ink 底 + paper 字
    case dark
    /// card 底 + line 描边 + ink 字
    case ghost
    /// 纯文字 mist
    case text
}

struct OMButtonPressStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .animation(OMTheme.Motion.fast, value: configuration.isPressed)
    }
}

/// CTA 要么有注入动作，要么有可见的禁用原因。
struct OMButton: View {
    let title: String
    var icon: OMIcon? = nil
    /// 生产视图需要设计稿 21 图标之外的 SF Symbol 时使用
    var systemIcon: String? = nil
    var kind: OMButtonKind = .primary
    var small = false
    var fillsWidth = true
    var loading = false
    var disabledReason: String? = nil
    let action: () -> Void

    init(
        _ title: String,
        icon: OMIcon? = nil,
        systemIcon: String? = nil,
        kind: OMButtonKind = .primary,
        small: Bool = false,
        fillsWidth: Bool = true,
        loading: Bool = false,
        disabledReason: String? = nil,
        action: @escaping () -> Void
    ) {
        self.title = title
        self.icon = icon
        self.systemIcon = systemIcon
        self.kind = kind
        self.small = small
        self.fillsWidth = fillsWidth
        self.loading = loading
        self.disabledReason = disabledReason
        self.action = action
    }

    private var isEnabled: Bool { disabledReason == nil && !loading }

    var body: some View {
        VStack(spacing: 5) {
            Button(action: action) {
                HStack(spacing: 8) {
                    if loading {
                        ProgressView().tint(foreground)
                    } else if let icon {
                        Image(om: icon)
                    } else if let systemIcon {
                        Image(systemName: systemIcon)
                    }
                    Text(title)
                }
                .font(small ? OMTheme.TypeToken.callout.weight(.semibold) : OMTheme.TypeToken.body.weight(.bold))
                .foregroundStyle(foreground)
                .frame(maxWidth: fillsWidth ? .infinity : nil)
                .frame(minHeight: small ? 38 : (kind == .text ? 44 : 52))
                .padding(.horizontal, fillsWidth ? 0 : 18)
                .background(background)
                .clipShape(Capsule())
                .overlay { Capsule().stroke(border, lineWidth: border == .clear ? 0 : OMTheme.Radius.borderWidth) }
            }
            .buttonStyle(OMButtonPressStyle())
            .disabled(!isEnabled)
            .opacity(disabledReason == nil ? 1 : 0.45)
            .accessibilityHint(disabledReason ?? "")

            if let disabledReason {
                Text(disabledReason)
                    .font(OMTheme.TypeToken.caption)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
            }
        }
    }

    private var background: Color {
        switch kind {
        case .primary: OMTheme.ColorToken.yolk
        case .dark: OMTheme.ColorToken.ink
        case .ghost: OMTheme.ColorToken.card
        case .text: .clear
        }
    }

    private var foreground: Color {
        switch kind {
        case .primary, .ghost: OMTheme.ColorToken.ink
        case .dark: OMTheme.ColorToken.paper
        case .text: OMTheme.ColorToken.mist
        }
    }

    private var border: Color {
        switch kind {
        case .primary: OMTheme.ColorToken.yolkBorder
        case .ghost: OMTheme.ColorToken.line
        case .dark, .text: .clear
        }
    }
}

// MARK: - 标签与缺口徽章（.om-chip / .gap-badge）

enum OMChipKind {
    case standard, solid, gap, soft
}

struct OMChip: View {
    let text: String
    var kind: OMChipKind = .standard
    var sticker: String? = nil

    var body: some View {
        HStack(spacing: 5) {
            if let sticker {
                LuluStickerImage(sticker)
                    .frame(width: 14, height: 14)
            }
            Text(text)
        }
        .font(OMTheme.TypeToken.caption.weight(.bold))
        .padding(.horizontal, 10)
        .padding(.vertical, 4)
        .background(background)
        .foregroundStyle(foreground)
        .clipShape(Capsule())
        .overlay { Capsule().stroke(border, lineWidth: border == .clear ? 0 : OMTheme.Radius.borderWidth) }
        .fixedSize()
    }

    private var background: Color {
        switch kind {
        case .standard: OMTheme.ColorToken.card
        case .solid: OMTheme.ColorToken.ink
        case .gap: OMTheme.ColorToken.yolk
        case .soft: OMTheme.ColorToken.gapSoft
        }
    }

    private var foreground: Color {
        switch kind {
        case .standard: OMTheme.ColorToken.mist
        case .solid: OMTheme.ColorToken.paper
        case .gap, .soft: OMTheme.ColorToken.ink
        }
    }

    private var border: Color {
        switch kind {
        case .standard: OMTheme.ColorToken.line
        case .solid: OMTheme.ColorToken.ink
        case .gap: OMTheme.ColorToken.yolkBorder
        case .soft: .clear
        }
    }
}

/// 「还缺 N 人」—— 全屏最高视觉权重的缺口徽章
struct OMGapBadge: View {
    let count: Int
    var label = "还缺"
    var customText: String? = nil
    /// 更细的胶囊：用于首屏待办等窄行场景。
    var compact = false

    /// 自定义文案形态（如「差你 1 票」）
    init(text: String, compact: Bool = false) {
        self.count = 0
        self.customText = text
        self.compact = compact
    }

    init(count: Int, label: String = "还缺", compact: Bool = false) {
        self.count = count
        self.label = label
        self.compact = compact
    }

    var body: some View {
        Group {
            if let customText {
                Text(customText)
            } else {
                HStack(spacing: compact ? 3 : 6) {
                    Text(label)
                    Text("\(count)").font(OMTheme.TypeToken.mono(compact ? .caption : .subheadline, weight: .bold))
                    Text("人")
                }
            }
        }
        .font((compact ? OMTheme.TypeToken.caption : OMTheme.TypeToken.footnote).weight(.heavy))
        .foregroundStyle(OMTheme.ColorToken.ink)
        .padding(.horizontal, compact ? 8 : 12)
        .padding(.vertical, compact ? 2 : 5)
        .background(OMTheme.ColorToken.yolk)
        .clipShape(Capsule())
        .overlay { Capsule().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth) }
        .accessibilityElement(children: .combine)
    }
}

/// 缺口英雄数字（.gap-hero：黄底 mono 大字 + 说明）
struct OMGapHero: View {
    let number: Int
    let suffix: String

    init(_ number: Int, suffix: String) {
        self.number = number
        self.suffix = suffix
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 6) {
            Text("\(number)")
                .font(.system(size: 44, weight: .heavy, design: .monospaced))
                .padding(.horizontal, 10)
                .padding(.vertical, 2)
                .background(OMTheme.ColorToken.yolk)
                .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
            Text(suffix)
                .font(OMTheme.TypeToken.mono(.title3))
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .accessibilityElement(children: .combine)
    }
}

/// 独立进度条（.om-progress）
struct OMProgressBar: View {
    let value: Double

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .leading) {
                Capsule().fill(OMTheme.ColorToken.line).frame(height: 8)
                Capsule()
                    .fill(OMTheme.ColorToken.ink)
                    .frame(width: geo.size.width * min(1, max(0, value)), height: 8)
            }
        }
        .frame(height: 8)
        .accessibilityLabel("进度")
        .accessibilityValue("\(Int(value * 100))%")
    }
}

// MARK: - 筛选 Pill

struct OMPill: View {
    let title: String
    var selected = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(OMTheme.TypeToken.footnote.weight(.semibold))
                .foregroundStyle(selected ? OMTheme.ColorToken.paper : OMTheme.ColorToken.mist)
                .padding(.horizontal, 14)
                .frame(height: 34)
                .background(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
                .clipShape(Capsule())
                .overlay { Capsule().stroke(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
        }
        .buttonStyle(OMButtonPressStyle())
    }
}

/// 标签与筛选组的紧凑换行布局
struct OMFlowLayout: Layout {
    var horizontalSpacing: CGFloat = 7
    var verticalSpacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? .infinity
        var cursorX: CGFloat = 0
        var cursorY: CGFloat = 0
        var rowHeight: CGFloat = 0
        var measuredWidth: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if cursorX > 0, cursorX + size.width > width {
                cursorX = 0
                cursorY += rowHeight + verticalSpacing
                rowHeight = 0
            }
            measuredWidth = max(measuredWidth, cursorX + size.width)
            cursorX += size.width + horizontalSpacing
            rowHeight = max(rowHeight, size.height)
        }
        return CGSize(width: proposal.width ?? measuredWidth, height: cursorY + rowHeight)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var cursorX = bounds.minX
        var cursorY = bounds.minY
        var rowHeight: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if cursorX > bounds.minX, cursorX + size.width > bounds.maxX {
                cursorX = bounds.minX
                cursorY += rowHeight + verticalSpacing
                rowHeight = 0
            }
            subview.place(at: CGPoint(x: cursorX, y: cursorY), anchor: .topLeading, proposal: ProposedViewSize(size))
            cursorX += size.width + horizontalSpacing
            rowHeight = max(rowHeight, size.height)
        }
    }
}

// MARK: - 导航（.om-nav / .om-large-title）

struct OMNavBar: View {
    let title: String
    var onBack: (() -> Void)? = nil
    var trailing: AnyView?

    init(title: String, onBack: (() -> Void)? = nil, trailing: AnyView? = nil) {
        self.title = title
        self.onBack = onBack
        self.trailing = trailing
    }

    init<Trailing: View>(title: String, onBack: (() -> Void)? = nil, @ViewBuilder trailing: () -> Trailing) {
        self.title = title
        self.onBack = onBack
        self.trailing = AnyView(trailing())
    }

    var body: some View {
        HStack(spacing: 12) {
            if let onBack {
                Button(action: onBack) {
                    Image(om: .back)
                        .font(.system(size: 15, weight: .semibold))
                        .frame(width: 36, height: 36)
                        .background(OMTheme.ColorToken.card)
                        .clipShape(Circle())
                        .overlay { Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
                }
                .buttonStyle(OMButtonPressStyle())
                .accessibilityLabel("返回")
            }
            Text(title)
                .font(OMTheme.TypeToken.title3)
                .tracking(-0.2)
            Spacer()
            if let trailing { trailing }
        }
        .padding(.horizontal, OMTheme.Spacing.pageX)
        .padding(.top, 4)
        .padding(.bottom, 10)
        .frame(minHeight: 44)
    }
}

struct OMLargeTitle: View {
    let title: String
    var sub: String? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            Text(title)
                .font(OMTheme.TypeToken.hero)
                .tracking(-0.7)
                .lineSpacing(2)
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.top, 2)
                .padding(.bottom, sub == nil ? 12 : 4)
            if let sub {
                Text(sub)
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.bottom, 12)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

/// 分组标题（.om-section）
struct OMSection: View {
    let title: String
    var more: (label: String, action: () -> Void)? = nil

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title.uppercased())
                .font(OMTheme.TypeToken.footnote.weight(.bold))
                .tracking(0.8)
                .foregroundStyle(OMTheme.ColorToken.mist)
            Spacer()
            if let more {
                Button(action: more.action) {
                    Text(more.label)
                        .font(OMTheme.TypeToken.footnote.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 2)
        .padding(.top, OMTheme.Spacing.s5)
        .padding(.bottom, OMTheme.Spacing.s2)
    }
}

// MARK: - 开关 / 分段 / 输入（.om-switch / .om-seg / .om-input）

struct OMSwitch: View {
    @Binding var isOn: Bool
    /// 嵌在整行可点的 `OMRow` 里时关掉，避免按钮套按钮连点两次。
    var interactive: Bool = true

    var body: some View {
        let knob = ZStack(alignment: isOn ? .trailing : .leading) {
            Capsule()
                .fill(isOn ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                .frame(width: 50, height: 30)
            Circle()
                .fill(OMTheme.ColorToken.card)
                .frame(width: 24, height: 24)
                .padding(3)
        }
        .frame(width: 50, height: 30)

        if interactive {
            Button {
                withAnimation(OMTheme.Motion.fast) { isOn.toggle() }
            } label: {
                knob
            }
            .buttonStyle(.plain)
            .accessibilityLabel("开关")
            .accessibilityValue(isOn ? "已开启" : "已关闭")
            .accessibilityAddTraits(.isButton)
        } else {
            knob.accessibilityHidden(true)
        }
    }
}

struct OMSeg<Item: Hashable>: View {
    let items: [Item]
    var label: (Item) -> String
    @Binding var selection: Item

    var body: some View {
        HStack(spacing: 2) {
            ForEach(items, id: \.self) { item in
                Button {
                    withAnimation(OMTheme.Motion.fast) { selection = item }
                } label: {
                    Text(label(item))
                        .font(OMTheme.TypeToken.footnote.weight(.semibold))
                        .foregroundStyle(selection == item ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
                        .frame(maxWidth: .infinity, minHeight: 34)
                        .background(selection == item ? OMTheme.ColorToken.card : .clear)
                        .clipShape(Capsule())
                        .shadow(color: selection == item ? OMTheme.ColorToken.ink.opacity(0.12) : .clear, radius: 2, y: 1)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(3)
        .background(OMTheme.ColorToken.ink06)
        .clipShape(Capsule())
    }
}

struct OMInputStyle: ViewModifier {
    var multiline = false

    func body(content: Content) -> some View {
        content
            .font(OMTheme.TypeToken.body)
            .foregroundStyle(OMTheme.ColorToken.ink)
            .padding(.horizontal, OMTheme.Spacing.s4)
            .padding(.vertical, multiline ? OMTheme.Spacing.s3 : 0)
            .frame(minHeight: multiline ? 96 : 52, alignment: multiline ? .topLeading : .center)
            .background(OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                    .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
    }
}

extension View {
    func omInputStyle(multiline: Bool = false) -> some View {
        modifier(OMInputStyle(multiline: multiline))
    }
}

// MARK: - Toast（.om-toast）

struct OMToastModifier: ViewModifier {
    @Binding var message: String?

    func body(content: Content) -> some View {
        content.overlay(alignment: .bottom) {
            if let message {
                Text(message)
                    .font(OMTheme.TypeToken.footnote.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.paper)
                    .padding(.horizontal, 18)
                    .padding(.vertical, 10)
                    .background(OMTheme.ColorToken.ink)
                    .clipShape(Capsule())
                    .padding(.bottom, 110)
                    .transition(.opacity.combined(with: .move(edge: .bottom)))
                    .onAppear {
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.8) {
                            withAnimation(OMTheme.Motion.medium) { self.message = nil }
                        }
                    }
            }
        }
        .animation(OMTheme.Motion.medium, value: message)
    }
}

extension View {
    func omToast(_ message: Binding<String?>) -> some View {
        modifier(OMToastModifier(message: message))
    }
}

// MARK: - 底部 Tab（.tabbar：五格 + 中央「差一个」）

enum OMTab: String, CaseIterable {
    case today = "今天"
    case match = "比赛"
    case create = "差一个"
    case msg = "消息"
    case me = "我"

    var icon: OMIcon {
        switch self {
        case .today: .sun
        case .match: .trophy
        case .create: .plus
        case .msg: .chat
        case .me: .person
        }
    }
}

struct OMTabBar: View {
    let selected: OMTab
    let onSelect: (OMTab) -> Void
    var hasMessage = false

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            ForEach(OMTab.allCases, id: \.self) { tab in
                if tab == .create {
                    createButton
                } else {
                    tabItem(tab)
                }
            }
        }
        .padding(.top, 8)
        .padding(.bottom, 20)
        .frame(maxWidth: .infinity)
        .background {
            OMTheme.ColorToken.card.opacity(0.92)
                .background(.ultraThinMaterial)
                .ignoresSafeArea(edges: .bottom)
        }
        .overlay(alignment: .top) {
            Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
        }
    }

    private var createButton: some View {
        Button { onSelect(.create) } label: {
            VStack(spacing: 3) {
                ZStack {
                    Circle()
                        .fill(OMTheme.ColorToken.yolk)
                        .frame(width: 52, height: 52)
                        .overlay { Circle().stroke(OMTheme.ColorToken.yolkBorderStrong, lineWidth: OMTheme.Radius.borderWidth) }
                        .shadow(color: OMTheme.ColorToken.yolk.opacity(0.55), radius: 8, y: 6)
                    Image(om: .plus)
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                }
                .padding(.top, -14)
                Text(OMTab.create.rawValue)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(OMButtonPressStyle())
        .accessibilityLabel("差一个，新建意图")
    }

    private func tabItem(_ tab: OMTab) -> some View {
        let active = selected == tab
        return Button { onSelect(tab) } label: {
            VStack(spacing: 3) {
                ZStack(alignment: .topTrailing) {
                    Image(om: tab.icon)
                        .font(.system(size: 22, weight: .regular))
                        .frame(width: 25, height: 25)
                    if tab == .msg && hasMessage {
                        Circle()
                            .fill(OMTheme.ColorToken.yolk)
                            .frame(width: 7, height: 7)
                            .overlay { Circle().stroke(OMTheme.ColorToken.card, lineWidth: 1.5) }
                            .offset(x: 4, y: -2)
                    }
                }
                .padding(.top, 6)
                Text(tab.rawValue)
                    .font(.system(size: 10, weight: .semibold))
                Circle()
                    .fill(OMTheme.ColorToken.yolk)
                    .frame(width: 4, height: 4)
                    .opacity(active ? 1 : 0)
            }
            .foregroundStyle(active ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
            .frame(maxWidth: .infinity)
            .frame(minHeight: 48)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(tab.rawValue)
        .accessibilityAddTraits(active ? .isSelected : [])
    }
}
