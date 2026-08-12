import SwiftUI

// MARK: - 卡片（.om-card）

struct OMCard<Content: View>: View {
    var tight = false
    var flat = false
    var background: Color? = nil
    var borderColor: Color? = nil
    var borderWidth: CGFloat? = nil
    let content: Content

    init(
        tight: Bool = false,
        flat: Bool = false,
        background: Color? = nil,
        borderColor: Color? = nil,
        borderWidth: CGFloat? = nil,
        @ViewBuilder content: () -> Content
    ) {
        self.tight = tight
        self.flat = flat
        self.background = background
        self.borderColor = borderColor
        self.borderWidth = borderWidth
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) { content }
            .padding(tight ? OMTheme.Spacing.s3 : OMTheme.Spacing.s4)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(flat ? .clear : (background ?? OMTheme.ColorToken.card))
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.large))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                    .stroke(borderColor ?? OMTheme.ColorToken.line, lineWidth: borderWidth ?? OMTheme.Radius.borderWidth)
            }
            .padding(.bottom, OMTheme.Spacing.s3)
    }
}

// MARK: - 列表行（.om-row）

struct OMRow: View {
    var icon: OMIcon? = nil
    var sticker: String? = nil
    let title: String
    var sub: String? = nil
    var right: String? = nil
    var toggle: Binding<Bool>? = nil
    var trailing: AnyView? = nil
    var onTap: (() -> Void)? = nil
    /// 底部分隔线；卡片末行 / 单行时应关掉，避免圆角内悬空横线。
    var showsDivider: Bool = true

    init(
        icon: OMIcon? = nil,
        sticker: String? = nil,
        title: String,
        sub: String? = nil,
        right: String? = nil,
        toggle: Binding<Bool>? = nil,
        showsDivider: Bool = true,
        onTap: (() -> Void)? = nil
    ) {
        self.icon = icon
        self.sticker = sticker
        self.title = title
        self.sub = sub
        self.right = right
        self.toggle = toggle
        self.showsDivider = showsDivider
        self.onTap = onTap
    }

    init(
        icon: OMIcon? = nil,
        sticker: String? = nil,
        title: String,
        sub: String? = nil,
        showsDivider: Bool = true,
        onTap: (() -> Void)? = nil,
        @ViewBuilder trailing: () -> some View
    ) {
        self.icon = icon
        self.sticker = sticker
        self.title = title
        self.sub = sub
        self.showsDivider = showsDivider
        self.onTap = onTap
        self.trailing = AnyView(trailing())
    }

    var body: some View {
        Button {
            onTap?()
        } label: {
            HStack(spacing: OMTheme.Spacing.s3) {
                if let sticker {
                    LuluStickerImage(sticker)
                        .frame(width: 26, height: 26)
                        .frame(width: 38, height: 38)
                        .background(OMTheme.ColorToken.readySoft)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                } else if let icon {
                    Image(om: icon)
                        .font(.system(size: 17))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .frame(width: 38, height: 38)
                        .background(OMTheme.ColorToken.readySoft)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                }
                VStack(alignment: .leading, spacing: 1) {
                    Text(title)
                        .font(OMTheme.TypeToken.callout.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    if let sub {
                        Text(sub)
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                if let toggle {
                    OMSwitch(isOn: toggle)
                } else if let trailing {
                    trailing
                } else if let right {
                    Text(right)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                if onTap != nil && toggle == nil {
                    Text("›")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundStyle(OMTheme.ColorToken.sage)
                }
            }
            .padding(.vertical, 13)
            .frame(minHeight: 48)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(onTap == nil)
        .overlay(alignment: .bottom) {
            if showsDivider {
                Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
            }
        }
    }
}

/// 步进行：标题 + −/+ 步进器（替代系统 Stepper，贴合设计稿）
struct OMStepperRow: View {
    let title: String
    @Binding var value: Int
    var range: ClosedRange<Int> = 2...20
    var step: Int = 1
    var unit: String = "人"

    var body: some View {
        HStack(spacing: OMTheme.Spacing.s3) {
            Text(title)
                .font(OMTheme.TypeToken.callout.weight(.semibold))
                .foregroundStyle(OMTheme.ColorToken.ink)
            Spacer()
            HStack(spacing: 0) {
                stepButton("minus", enabled: value - step >= range.lowerBound) {
                    value = max(range.lowerBound, value - step)
                }
                Text("\(value) \(unit)")
                    .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .frame(minWidth: 56)
                stepButton("plus", enabled: value + step <= range.upperBound) {
                    value = min(range.upperBound, value + step)
                }
            }
            .background(OMTheme.ColorToken.ink06)
            .clipShape(Capsule())
        }
        .padding(.vertical, 13)
        .frame(minHeight: 48)
        .overlay(alignment: .bottom) {
            Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
        }
    }

    private func stepButton(_ systemName: String, enabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: { withAnimation(OMTheme.Motion.fast, action) }) {
            Image(systemName: systemName)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(enabled ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                .frame(width: 34, height: 34)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
        .accessibilityLabel(systemName == "plus" ? "增加" : "减少")
    }
}

/// 一组 om-row，末行去掉分隔线
struct OMRowGroup<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        VStack(spacing: 0) { content }
    }
}

// MARK: - 圆桌席位（签名组件 .seat-table）

struct OMSeat: Identifiable, Hashable {
    enum State: Hashable { case filled, gap }
    let id: String
    let role: String
    let state: State
    let sticker: String

    init(role: String, state: State, sticker: String) {
        self.id = "\(role)-\(state)"
        self.role = role
        self.state = state
        self.sticker = sticker
    }
}

private struct SeatPulse: ViewModifier {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulsing = false

    func body(content: Content) -> some View {
        content.overlay {
            if !reduceMotion {
                Circle()
                    .stroke(OMTheme.ColorToken.yolk, lineWidth: 2)
                    .scaleEffect(pulsing ? 1.35 : 1)
                    .opacity(pulsing ? 0 : 0.55)
                    .animation(
                        .timingCurve(0.22, 1, 0.36, 1, duration: 1.6).repeatForever(autoreverses: false),
                        value: pulsing
                    )
                    .onAppear { pulsing = true }
            }
        }
    }
}

struct OMSeatTable: View {
    let name: String
    let seats: [OMSeat]
    var tableSticker = "round-table.png"
    var size: CGFloat = 240

    var body: some View {
        let radius = size * (96.0 / 240.0)
        ZStack {
            // 桌面
            Circle()
                .fill(OMTheme.ColorToken.card)
                .overlay { Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
                .frame(width: size - 2 * 58 * (size / 240), height: size - 2 * 58 * (size / 240))
                .overlay {
                    VStack(spacing: 4) {
                        LuluStickerImage(tableSticker)
                            .frame(width: 54, height: 54)
                        Text(name)
                            .font(OMTheme.TypeToken.caption.weight(.bold))
                            .lineSpacing(1.5)
                            .multilineTextAlignment(.center)
                    }
                    .padding(10)
                }
            // 席位
            ForEach(Array(seats.enumerated()), id: \.element.id) { index, seat in
                let angle = -Double.pi / 2 + Double(index) * 2 * Double.pi / Double(seats.count)
                seatView(seat)
                    .position(
                        x: size / 2 + radius * cos(angle),
                        y: size / 2 + radius * sin(angle)
                    )
            }
        }
        .frame(width: size, height: size)
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(name)：\(seats.filter { $0.state == .filled }.count) 人已就位，缺 \(seats.filter { $0.state == .gap }.count) 人")
    }

    private func seatView(_ seat: OMSeat) -> some View {
        VStack(spacing: 3) {
            ZStack {
                Circle()
                    .fill(seat.state == .gap ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.ink)
                    .frame(width: 44, height: 44)
                    .overlay {
                        Circle().stroke(
                            seat.state == .gap ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.ink,
                            lineWidth: 2
                        )
                    }
                // 已就位：贴纸以纸色剪影落在墨点上；缺口：贴纸原色落在黄点上
                if seat.state == .filled {
                    LuluStickerImage(seat.sticker, template: true)
                        .foregroundStyle(OMTheme.ColorToken.paper)
                        .frame(width: 26, height: 26)
                } else {
                    LuluStickerImage(seat.sticker)
                        .frame(width: 26, height: 26)
                }
            }
            .modifier(SeatPulse())
            .opacity(seat.state == .gap ? 1 : 1)
            Text(seat.state == .gap ? "缺 · \(seat.role)" : seat.role)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(seat.state == .gap ? OMTheme.ColorToken.ink : (seat.state == .filled ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist))
                .padding(.horizontal, seat.state == .gap ? 7 : 0)
                .padding(.vertical, seat.state == .gap ? 1 : 0)
                .background(seat.state == .gap ? OMTheme.ColorToken.gapSoft : .clear)
                .clipShape(Capsule())
                .fixedSize()
        }
        .frame(width: 56)
    }
}

/// 紧凑型席位条（列表卡内嵌 .seat-strip）
struct OMSeatStrip: View {
    let seats: [OMSeat]

    var body: some View {
        HStack(spacing: 6) {
            ForEach(seats) { seat in
                ZStack {
                    Circle()
                        .fill(seat.state == .gap ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.ink)
                        .frame(width: 26, height: 26)
                    if seat.state == .filled {
                        LuluStickerImage(seat.sticker, template: true)
                            .foregroundStyle(OMTheme.ColorToken.paper)
                            .frame(width: 15, height: 15)
                    } else {
                        LuluStickerImage(seat.sticker)
                            .frame(width: 15, height: 15)
                    }
                }
                .accessibilityLabel("\(seat.role)\(seat.state == .gap ? "（缺口）" : "（已就位）")")
            }
        }
    }
}

/// 匿名人数席位条：已进池的席位用静态 Lulu 头像（不代表具体是谁），
/// 空位用虚线圈。配合「X/Y · 状态」文案表达规模与进度，不暴露身份。
struct OMLuluSeatStrip: View {
    let filled: Int
    let total: Int
    var size: CGFloat = 26

    var body: some View {
        HStack(spacing: 6) {
            ForEach(0..<max(total, 0), id: \.self) { index in
                if index < filled {
                    ZStack {
                        Circle().fill(OMTheme.ColorToken.card)
                        LuluStickerImage("lulu-face.png")
                            .padding(1.5)
                        Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .frame(width: size, height: size)
                    .accessibilityLabel("席位 \(index + 1)，已有人")
                } else {
                    Circle()
                        .stroke(style: StrokeStyle(lineWidth: 1.5, dash: [3, 3]))
                        .foregroundStyle(OMTheme.ColorToken.mist.opacity(0.55))
                        .frame(width: size, height: size)
                        .accessibilityLabel("席位 \(index + 1)，空缺")
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("已进 \(filled) 人，共 \(total) 人局")
    }
}

// MARK: - 进度（.om-progress + 就位计数）

struct OMReadiness: View {
    let ready: Int
    let total: Int

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("已就位 ")
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                + Text("\(ready)").font(OMTheme.TypeToken.mono(.footnote, weight: .bold)).foregroundStyle(OMTheme.ColorToken.ink)
                + Text(" / \(total)").font(OMTheme.TypeToken.footnote).foregroundStyle(OMTheme.ColorToken.mist)
                Spacer()
                if ready < total {
                    OMGapBadge(count: total - ready)
                } else {
                    OMChip(text: "已满员", kind: .solid)
                }
            }
            .padding(.bottom, OMTheme.Spacing.s2)
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    Capsule().fill(OMTheme.ColorToken.line).frame(height: 8)
                    Capsule()
                        .fill(OMTheme.ColorToken.ink)
                        .frame(width: geo.size.width * min(1, Double(ready) / Double(max(total, 1))), height: 8)
                }
            }
            .frame(height: 8)
        }
        .accessibilityElement(children: .combine)
    }
}

// MARK: - 页脚说明条（.om-note）

struct OMNote: View {
    let text: String
    var sticker = "chat-bubble.png"

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            LuluStickerImage(sticker)
                .frame(width: 18, height: 18)
                .padding(.top, 1)
            Text(text)
                .font(OMTheme.TypeToken.footnote)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .lineSpacing(3)
                .frame(maxWidth: .infinity, alignment: .leading)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(OMTheme.ColorToken.ink06)
        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
    }
}

// MARK: - 时间轴（.om-timeline）

struct OMTimelineItem: Identifiable {
    enum State { case done, now, upcoming }
    let id = UUID()
    let state: State
    let title: String
    var detail: String? = nil
}

struct OMTimeline: View {
    let items: [OMTimelineItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                HStack(alignment: .top, spacing: 10) {
                    ZStack {
                        if index < items.count - 1 {
                            Rectangle()
                                .fill(OMTheme.ColorToken.line)
                                .frame(width: 2)
                                .offset(y: 12)
                        }
                        Circle()
                            .fill(dotFill(item.state))
                            .frame(width: 12, height: 12)
                            .overlay { Circle().stroke(dotStroke(item.state), lineWidth: 2) }
                    }
                    .frame(width: 12)
                    .padding(.top, 5)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(item.title)
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        if let detail = item.detail {
                            Text(detail)
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                    }
                    .padding(.bottom, OMTheme.Spacing.s4)
                    Spacer(minLength: 0)
                }
            }
        }
    }

    private func dotFill(_ state: OMTimelineItem.State) -> Color {
        switch state {
        case .done: OMTheme.ColorToken.ink
        case .now: OMTheme.ColorToken.yolk
        case .upcoming: OMTheme.ColorToken.card
        }
    }

    private func dotStroke(_ state: OMTimelineItem.State) -> Color {
        switch state {
        case .done: OMTheme.ColorToken.ink
        case .now: OMTheme.ColorToken.yolk
        case .upcoming: OMTheme.ColorToken.sage
        }
    }
}

// MARK: - 日历横条（.cal-strip）

struct OMCalDay: Identifiable {
    let id: String
    let day: String
    let weekday: String
    var selected = false
    var dots = 0
}

struct OMCalStrip: View {
    let days: [OMCalDay]
    var onSelect: ((OMCalDay) -> Void)? = nil

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(days) { day in
                    Button {
                        onSelect?(day)
                    } label: {
                        VStack(spacing: 2) {
                            Text(day.day)
                                .font(OMTheme.TypeToken.mono(.headline, weight: .bold))
                            Text(day.weekday)
                                .font(.system(size: 10))
                                .foregroundStyle(day.selected ? OMTheme.ColorToken.paper : OMTheme.ColorToken.mist)
                            HStack(spacing: 2) {
                                ForEach(0..<max(day.dots, 0), id: \.self) { _ in
                                    Circle().fill(OMTheme.ColorToken.yolk).frame(width: 4, height: 4)
                                }
                            }
                            .frame(height: 4)
                            .padding(.top, 2)
                        }
                        .frame(width: 52)
                        .padding(.vertical, 8)
                        .background(day.selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
                        .foregroundStyle(day.selected ? OMTheme.ColorToken.paper : OMTheme.ColorToken.ink)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
                        .overlay {
                            RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                                .stroke(day.selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.bottom, 4)
        }
    }
}

// MARK: - 课表格子（.schedule-grid）

struct OMScheduleCell: Identifiable {
    enum Kind { case head, time, empty, has, free }
    let id = UUID()
    let kind: Kind
    let text: String
    var selected = false
    var onTap: (() -> Void)? = nil

    init(_ kind: Kind, _ text: String = "", selected: Bool = false, onTap: (() -> Void)? = nil) {
        self.kind = kind
        self.text = text
        self.selected = selected
        self.onTap = onTap
    }
}

struct OMScheduleGrid: View {
    /// rows 每行 6 格：时间列 + 5 天
    let rows: [[OMScheduleCell]]

    private let columns: [GridItem] = [GridItem(.fixed(34))] + Array(repeating: GridItem(.flexible(), spacing: 3), count: 5)

    var body: some View {
        LazyVGrid(columns: columns, spacing: 3) {
            ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                ForEach(row) { cell in
                    cellView(cell)
                }
            }
        }
        .font(.system(size: 10))
    }

    @ViewBuilder private func cellView(_ cell: OMScheduleCell) -> some View {
        switch cell.kind {
        case .head:
            Text(cell.text)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(OMTheme.ColorToken.mist)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 4)
        case .time:
            Text(cell.text)
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(OMTheme.ColorToken.mist)
                .frame(maxWidth: .infinity, alignment: .trailing)
                .padding(.trailing, 4)
        case .empty, .has, .free:
            Text(cell.text)
                .font(.system(size: 10, weight: .semibold))
                .lineSpacing(1.2)
                .foregroundStyle(foreground(cell.kind))
                .frame(maxWidth: .infinity, minHeight: 44, alignment: .topLeading)
                .padding(.horizontal, 4)
                .padding(.vertical, 3)
                .background(background(cell.kind))
                .clipShape(RoundedRectangle(cornerRadius: 6))
                .overlay {
                    RoundedRectangle(cornerRadius: 6)
                        .stroke(border(cell.kind), style: StrokeStyle(lineWidth: cell.selected ? 2 : OMTheme.Radius.borderWidth, dash: cell.kind == .free && !cell.selected ? [4, 3] : []))
                }
                .onTapGesture { cell.onTap?() }
        }
    }

    private func foreground(_ kind: OMScheduleCell.Kind) -> Color {
        switch kind {
        case .has: OMTheme.ColorToken.paper
        default: OMTheme.ColorToken.ink
        }
    }

    private func background(_ kind: OMScheduleCell.Kind) -> Color {
        switch kind {
        case .has: OMTheme.ColorToken.ink
        case .free: OMTheme.ColorToken.gapSoft
        default: OMTheme.ColorToken.card
        }
    }

    private func border(_ kind: OMScheduleCell.Kind) -> Color {
        switch kind {
        case .has: OMTheme.ColorToken.ink
        case .free: OMTheme.ColorToken.yolk
        default: OMTheme.ColorToken.line
        }
    }
}

// MARK: - 聊天气泡（.bubble / .bubble-sys）

/// Renders a subset of Markdown (bold / italic / lists / links) with a plain-text fallback.
struct OMMarkdownText: View {
    let text: String
    var font: Font = OMTheme.TypeToken.callout
    var color: Color = OMTheme.ColorToken.ink
    var lineSpacing: CGFloat = 4

    var body: some View {
        Text(Self.attributed(text, color: color))
            .font(font)
            .lineSpacing(lineSpacing)
            .multilineTextAlignment(.leading)
            .textSelection(.enabled)
    }

    static func attributed(_ raw: String, color: Color) -> AttributedString {
        let prepared = prepare(raw)
        var options = AttributedString.MarkdownParsingOptions()
        options.interpretedSyntax = .inlineOnlyPreservingWhitespace
        options.failurePolicy = .returnPartiallyParsedIfPossible
        if let parsed = try? AttributedString(markdown: prepared, options: options) {
            var copy = parsed
            copy.foregroundColor = color
            return copy
        }
        var plain = AttributedString(prepared)
        plain.foregroundColor = color
        return plain
    }

    /// Keep visual line breaks: Markdown `.full` collapses single newlines into spaces.
    private static func prepare(_ raw: String) -> String {
        var text = raw.replacingOccurrences(of: "\r\n", with: "\n")
        text = text.replacingOccurrences(
            of: #"([。！？；:：])\s*(\d+[\.、]\s)"#,
            with: "$1\n$2",
            options: .regularExpression
        )
        text = text.replacingOccurrences(
            of: #"([。！？])\s+([—\-•])"#,
            with: "$1\n$2",
            options: .regularExpression
        )
        return text
    }
}

/// .bubble / .bubble.me：无头像、无昵称、无时间、无已读回执
struct OMChatBubble: View {
    let text: String
    let isMine: Bool
    var markdown: Bool = false

    init(_ text: String, mine: Bool, markdown: Bool = false) {
        self.text = text
        self.isMine = mine
        self.markdown = markdown
    }

    var body: some View {
        HStack(spacing: 8) {
            if isMine { Spacer(minLength: 36) }
            Group {
                if markdown {
                    OMMarkdownText(
                        text: text,
                        font: OMTheme.TypeToken.callout,
                        color: isMine ? OMTheme.ColorToken.paper : OMTheme.ColorToken.ink
                    )
                } else {
                    Text(text)
                        .font(OMTheme.TypeToken.callout)
                        .lineSpacing(3)
                        .multilineTextAlignment(.leading)
                        .foregroundStyle(isMine ? OMTheme.ColorToken.paper : OMTheme.ColorToken.ink)
                }
            }
            .frame(maxWidth: isMine ? nil : .infinity, alignment: .leading)
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .background(isMine ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(isMine ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
            if !isMine { Spacer(minLength: 8) }
        }
    }
}

/// 系统消息泡（.bubble-sys）
struct OMSysBubble: View {
    let text: String

    var body: some View {
        Text(text)
            .font(OMTheme.TypeToken.footnote)
            .foregroundStyle(OMTheme.ColorToken.ink)
            .padding(.horizontal, 14)
            .padding(.vertical, 6)
            .background(OMTheme.ColorToken.gapSoft)
            .clipShape(Capsule())
            .frame(maxWidth: .infinity)
    }
}

// MARK: - 二维码占位（.qr-box，认证扫码用真实语义图形）

struct OMQRBox<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        content
            .frame(width: 168, height: 168)
            .padding(16)
            .background(OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                    .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
            .frame(maxWidth: .infinity)
    }
}

// MARK: - 底部弹层 chrome（.om-sheet）

struct OMSheet<Content: View>: View {
    let content: Content
    init(@ViewBuilder content: () -> Content) { self.content = content() }

    var body: some View {
        VStack(spacing: 0) {
            Capsule()
                .fill(OMTheme.ColorToken.line)
                .frame(width: 38, height: 5)
                .padding(.top, 12)
                .padding(.bottom, 12)
            content
        }
        .padding(.horizontal, OMTheme.Spacing.pageX)
        .padding(.bottom, 34)
        .frame(maxWidth: .infinity)
        .background(OMTheme.ColorToken.card)
        .clipShape(UnevenRoundedRectangle(topLeadingRadius: OMTheme.Radius.xLarge, topTrailingRadius: OMTheme.Radius.xLarge))
        .overlay {
            UnevenRoundedRectangle(topLeadingRadius: OMTheme.Radius.xLarge, topTrailingRadius: OMTheme.Radius.xLarge)
                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
        }
        .shadow(color: OMTheme.ColorToken.ink.opacity(0.14), radius: 20, y: -12)
    }
}

// MARK: - 贴纸尺寸档（.st-*）

enum OMStickerSize: CGFloat, CaseIterable {
    case s20 = 20, s24 = 24, s32 = 32, s44 = 44, s56 = 56, s72 = 72, s96 = 96
}

struct OMSticker: View {
    let id: String
    var size: OMStickerSize = .s44

    init(_ id: String, size: OMStickerSize = .s44) {
        self.id = id
        self.size = size
    }

    var body: some View {
        LuluStickerImage(id)
            .frame(width: size.rawValue, height: size.rawValue)
    }
}

// MARK: - 跨屏共享小组件（.divider / .nav-back / .chat-input / 文字角色）

/// .divider：卡内分段线
struct OMDivider: View {
    var body: some View {
        Rectangle()
            .fill(OMTheme.ColorToken.line)
            .frame(height: OMTheme.Radius.borderWidth)
            .padding(.vertical, OMTheme.Spacing.s4)
    }
}

/// .nav-back：圆形线框图标按钮（导航右侧 / 语音 / 发送）
struct OMIconButton: View {
    let icon: OMIcon
    var size: CGFloat = 36
    var accessibilityLabel: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(om: icon)
                .font(.system(size: size * 0.42, weight: .regular))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .frame(width: size, height: size)
                .background(OMTheme.ColorToken.card)
                .clipShape(Circle())
                .overlay { Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
        }
        .buttonStyle(OMButtonPressStyle())
        .accessibilityLabel(accessibilityLabel)
    }
}

/// 认证扫码占位图形：与设计稿内联 SVG 相同的 21×21 语义点阵
struct OMQRPattern: View {
    private static let cells: [(x: Int, y: Int, w: Int, h: Int)] = [
        (0, 0, 7, 7), (2, 2, 3, 3), (14, 0, 7, 7), (16, 2, 3, 3),
        (0, 14, 7, 7), (2, 16, 3, 3), (9, 0, 3, 3), (9, 5, 2, 2),
        (14, 9, 3, 2), (18, 9, 3, 3), (9, 9, 2, 3), (12, 10, 2, 2),
        (9, 14, 3, 2), (13, 13, 2, 2), (16, 14, 2, 2), (19, 14, 2, 2),
        (14, 17, 3, 2), (18, 18, 3, 3), (9, 18, 2, 3), (12, 19, 2, 2),
    ]

    var body: some View {
        Canvas { context, size in
            let unit = min(size.width, size.height) / 21
            for cell in Self.cells {
                let rect = CGRect(x: CGFloat(cell.x) * unit, y: CGFloat(cell.y) * unit,
                                  width: CGFloat(cell.w) * unit, height: CGFloat(cell.h) * unit)
                context.fill(Path(rect), with: .color(OMTheme.ColorToken.ink))
            }
        }
        .accessibilityLabel("企业微信扫码二维码")
    }
}

/// .chat-input：底部输入条（E14 用；B2/G1 内嵌在 footer/sheet 里）
struct OMChatInputBar: View {
    let placeholder: String
    var sendIcon: OMIcon = .arrow
    var onSend: () -> Void = {}
    @State private var text = ""

    var body: some View {
        HStack(spacing: 8) {
            TextField(placeholder, text: $text)
                .font(OMTheme.TypeToken.callout)
                .padding(.horizontal, 18)
                .frame(minHeight: 42)
                .background(OMTheme.ColorToken.card)
                .clipShape(Capsule())
                .overlay { Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
            OMIconButton(icon: sendIcon, size: 42, accessibilityLabel: "发送") {
                text = ""
                onSend()
            }
        }
        .padding(.horizontal, OMTheme.Spacing.pageX)
        .padding(.top, 10)
        .padding(.bottom, 30)
        .background(OMTheme.ColorToken.card)
        .overlay(alignment: .top) {
            Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
        }
    }
}

/// 设计稿文字角色速查：t-hero / t-t1 / t-t2 / t-t3 / t-call / t-foot / t-cap
enum OMTextRole {
    static func hero(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.hero).tracking(-0.7)
    }
    static func t1(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.title1).tracking(-0.3)
    }
    static func t2(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.title2).tracking(-0.2)
    }
    static func t3(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.title3)
    }
    static func call(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.callout).lineSpacing(3)
    }
    static func foot(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.footnote).foregroundStyle(OMTheme.ColorToken.mist).lineSpacing(2)
    }
    static func cap(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.caption).foregroundStyle(OMTheme.ColorToken.mist)
    }
    static func monoFoot(_ text: String) -> some View {
        Text(text).font(OMTheme.TypeToken.mono(.footnote)).foregroundStyle(OMTheme.ColorToken.mist)
    }
}

// MARK: - 稀疏确认页公式（标题 → 中间大噜噜 → 底部选项）

/// 选项少、下半屏易空的确认/选择页：上标题、中噜噜、下操作区。
struct OMStage<Footer: View>: View {
    let title: String
    var subtitle: String? = nil
    var clip: LuluClip = .homeReply
    @ViewBuilder var footer: () -> Footer

    var body: some View {
        VStack(spacing: 0) {
            Text(title)
                .font(OMTheme.TypeToken.title2)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s4)
                .padding(.horizontal, 24)
            if let subtitle, !subtitle.isEmpty {
                Text(subtitle)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 28)
                    .padding(.top, 6)
            }
            Spacer(minLength: 8)
            LuluView(clip: clip, placement: .hero)
                .frame(maxWidth: .infinity)
                .frame(height: 260)
            Spacer(minLength: 8)
            VStack(spacing: 10) { footer() }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 34)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(OMPageBackground())
    }
}

// MARK: - 生产页眉与系统组件（替代旧 NativeComponents）

/// 生产页眉：eyebrow 小 caps + t1 大标题（内容区内使用，无内置横向 padding）
struct OMHeader: View {
    let eyebrow: String?
    let title: String?
    let lulu: LuluClip?

    init(eyebrow: String? = nil, title: String? = nil, lulu: LuluClip? = nil) {
        self.eyebrow = eyebrow
        self.title = title
        self.lulu = lulu
    }

    var body: some View {
        HStack(alignment: .center, spacing: OMTheme.Spacing.s3) {
            VStack(alignment: .leading, spacing: 5) {
                if let eyebrow {
                    Text(eyebrow.uppercased())
                        .font(OMTheme.TypeToken.footnote.weight(.bold))
                        .tracking(1.6)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                if let title {
                    Text(title).font(OMTheme.TypeToken.title1).tracking(-0.3)
                }
            }
            Spacer(minLength: 0)
            if let lulu {
                LuluView(clip: lulu, placement: .avatar)
                    .accessibilityHidden(true)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .padding(.bottom, OMTheme.Spacing.s3)
    }
}

struct OMDebugRequestID: View {
    let requestID: String?
    var body: some View {
        #if DEBUG
        if let requestID {
            Button { UIPasteboard.general.string = requestID } label: {
                Label("请求 ID · 点按复制", systemImage: "doc.on.doc")
                    .font(OMTheme.TypeToken.caption)
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            .accessibilityLabel("复制请求诊断编号")
        }
        #endif
    }
}

struct OMPermissionRecoveryNotice: View {
    @ObservedObject var coordinator: PermissionCoordinator
    let permissions: Set<PermissionCoordinator.Permission>

    var body: some View {
        if !coordinator.denied.isDisjoint(with: permissions) {
            OMCard {
                HStack(spacing: 10) {
                    Image(om: .shield)
                        .font(.system(size: 17))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .frame(width: 38, height: 38)
                        .background(OMTheme.ColorToken.readySoft)
                        .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                    VStack(alignment: .leading, spacing: 2) {
                        OMTextRole.t3("权限未开启")
                        OMTextRole.foot("本次操作已停止；可稍后重试，或到系统设置恢复权限。")
                    }
                    Spacer()
                }
                OMButton("打开系统设置", kind: .ghost, small: true, fillsWidth: false) {
                    coordinator.openSystemSettings()
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
            .accessibilityIdentifier("permission-recovery-notice")
        }
    }
}
