import SwiftUI
import UIKit

// MARK: - 一句话心情

/// 匿名意图卡上的「一句话心情」：有温度但不携带身份。
struct MoodNoteQuote: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Rectangle()
                .fill(OMTheme.ColorToken.yolk)
                .frame(width: 3)
                .clipShape(Capsule())
            Text("“\(text)”")
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .lineSpacing(3)
        }
        .fixedSize(horizontal: false, vertical: true)
        .accessibilityLabel("发起人心情：\(text)")
    }
}

// MARK: - 桌与座

/// 「桌与座」核心隐喻：一排座位点，已就位实心、空位虚线呼吸。
struct SeatDotsView: View {
    let total: Int
    let filled: Int
    var animated = false

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var appeared = 0

    var body: some View {
        HStack(spacing: 10) {
            ForEach(0..<min(total, 8), id: \.self) { index in
                seat(index)
            }
        }
        .onAppear {
            guard animated, !reduceMotion else {
                appeared = filled
                return
            }
            for step in 0...filled {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.28 * Double(step)) {
                    withAnimation(.spring(response: 0.35, dampingFraction: 0.62)) {
                        appeared = step
                    }
                }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("座位 \(filled) / \(total) 已就位")
    }

    @ViewBuilder private func seat(_ index: Int) -> some View {
        let isFilled = index < (animated ? appeared : filled)
        Circle()
            .fill(isFilled ? OMTheme.ColorToken.ink : OMTheme.ColorToken.yolk.opacity(0.25))
            .overlay {
                if !isFilled {
                    Circle()
                        .strokeBorder(OMTheme.ColorToken.yolkBorder, style: StrokeStyle(lineWidth: 1.5, dash: [3, 3]))
                }
            }
            .frame(width: 15, height: 15)
            .scaleEffect(isFilled ? 1 : 0.92)
    }
}

// MARK: - 座满仪式

/// 每个局在一次 App 会话内只庆祝一次；纯本地状态，不写服务端。
@MainActor enum GatheringCelebrationTracker {
    private static var celebrated: Set<String> = []

    /// 首次标记返回 true，之后同一局返回 false。
    static func markCelebrated(_ gatheringID: String) -> Bool {
        celebrated.insert(gatheringID).inserted
    }
}

/// A3 · 成局瞬间的「座满」全屏仪式：空椅 → 落座 → 噜噜庆祝退场。
/// 全产品最该砸的 3 秒。Reduce Motion 时静帧呈现，不做步进动画。
struct GatheringCelebrationOverlay: View {
    let gathering: GatheringSummary
    let onEnterIcebreaker: () -> Void
    let onDismiss: () -> Void

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var stage = 0
    @State private var luluClip: LuluClip = .confirmGather

    var body: some View {
        ZStack {
            OMPageBackground().ignoresSafeArea()
            VStack(spacing: 0) {
                Spacer()
                Text("\(AppBrand.displayName) · \(AppBrand.coreAction)")
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .tracking(3)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                ZStack {
                    Circle()
                        .stroke(OMTheme.ColorToken.ink, lineWidth: 2)
                        .background {
                            Circle().fill(OMTheme.ColorToken.yolk.opacity(stage >= 1 ? 0.22 : 0.08))
                        }
                        .frame(width: 168, height: 168)
                    Circle()
                        .strokeBorder(OMTheme.ColorToken.line, style: StrokeStyle(lineWidth: 1.5, dash: [4, 4]))
                        .frame(width: 116, height: 116)
                    LuluView(clip: luluClip, placement: .confirm)
                        .scaleEffect(stage >= 1 ? 1 : 0.7)
                        .opacity(stage >= 1 ? 1 : 0)
                }
                .padding(.top, 26)
                SeatDotsView(total: gathering.targetSize, filled: gathering.targetSize, animated: !reduceMotion)
                    .padding(.top, 22)
                Text("凑齐了！")
                    .font(.system(size: 40, weight: .heavy))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, 14)
                    .scaleEffect(stage >= 2 ? 1 : 0.86)
                    .opacity(stage >= 2 ? 1 : 0)
                Text("\(gathering.targetSize) 个人的「\(gathering.title)」正式成局")
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .padding(.top, 6)
                    .opacity(stage >= 2 ? 1 : 0)
                if let participants = gathering.participants, stage >= 3 {
                    memberChips(participants)
                        .padding(.top, 18)
                        .transition(.opacity.combined(with: .move(edge: .bottom)))
                }
                Spacer()
                if stage >= 3 {
                    VStack(spacing: 10) {
                        OMButton("看看为什么是你们", systemIcon: "sparkles") {
                            onEnterIcebreaker()
                        }
                        OMButton("稍后再说", kind: .text) { onDismiss() }
                    }
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.bottom, 30)
                    .transition(.opacity)
                }
            }
        }
        .onAppear { runSequence() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("gathering-celebration-overlay")
    }

    @ViewBuilder private func memberChips(_ participants: [GatheringSummary.Participant]) -> some View {
        VStack(spacing: 8) {
            Text("这一桌")
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
            HStack(spacing: 8) {
                ForEach(participants.prefix(4)) { person in
                    OMChip(text: person.displayName ?? "同学", kind: .soft)
                }
            }
        }
    }

    private func runSequence() {
        UINotificationFeedbackGenerator().notificationOccurred(.success)
        guard !reduceMotion else {
            stage = 3
            luluClip = .confirmGather
            return
        }
        let seatDelay = 0.28 * Double(min(gathering.targetSize, 8)) + 0.2
        withAnimation(.spring(response: 0.45, dampingFraction: 0.7).delay(0.1)) { stage = 1 }
        withAnimation(.spring(response: 0.4, dampingFraction: 0.65).delay(seatDelay)) { stage = 2 }
        withAnimation(.easeOut(duration: 0.35).delay(seatDelay + 0.8)) { stage = 3 }
        // 噜噜庆祝完鞠躬退场：成局后 IP 让位给真人（红线 17 的仪式化表达）。
        DispatchQueue.main.asyncAfter(deadline: .now() + seatDelay + 2.4) {
            luluClip = .exitBow
        }
    }
}

// MARK: - 破冰包

/// B · 成局后 30 秒第一屏：为什么是你们 / 第一句可以这样开 / 下一步是什么。
struct IcebreakerCardView: View {
    let pack: IcebreakerPack
    var onOpenChannel: ((String) -> Void)? = nil

    @State private var copiedLine: String?

    var body: some View {
        OMCard {
            HStack(spacing: 8) {
                OMSticker("chat-bubble.png", size: .s44)
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("为什么是你们")
                    OMTextRole.cap(pack.headline)
                }
                Spacer()
            }
            if !pack.facts.isEmpty {
                FlowChips(items: pack.facts.map(\.text))
                    .padding(.top, OMTheme.Spacing.s3)
            }
            OMDivider()
            OMTextRole.t3("第一句可以这样开")
            ForEach(pack.firstLines, id: \.self) { line in
                Button {
                    UIPasteboard.general.string = line
                    withAnimation(.easeOut(duration: 0.2)) { copiedLine = line }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.6) {
                        withAnimation { if copiedLine == line { copiedLine = nil } }
                    }
                } label: {
                    HStack(alignment: .top, spacing: 8) {
                        Text("“\(line)”")
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .multilineTextAlignment(.leading)
                            .lineSpacing(3)
                        Spacer(minLength: 8)
                        Image(systemName: copiedLine == line ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(copiedLine == line ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
                    }
                    .padding(10)
                    .background(OMTheme.ColorToken.gapSoft)
                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityLabel("开场白模板：\(line)，点按复制")
            }
            OMDivider()
            OMTextRole.t3("下一步")
            ForEach(pack.nextSteps.checklist, id: \.self) { step in
                HStack(spacing: 8) {
                    Image(systemName: "checkmark.circle")
                        .font(.system(size: 13))
                        .foregroundStyle(OMTheme.ColorToken.sage)
                    Text(step)
                }
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, 4)
            }
            if let channelID = pack.nextSteps.channelId, let onOpenChannel {
                OMButton("带着第一句进群聊", systemIcon: "message", small: true, fillsWidth: false) {
                    onOpenChannel(channelID)
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("gathering-icebreaker-card")
    }
}

/// 简单的自动换行 chips 布局。
struct FlowChips: View {
    let items: [String]

    var body: some View {
        FlowLayout(spacing: 6) {
            ForEach(items, id: \.self) { item in
                OMChip(text: item, kind: .soft)
            }
        }
    }
}

struct FlowLayout: Layout {
    var spacing: CGFloat = 6

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        arrange(proposal: proposal, subviews: subviews).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        let result = arrange(proposal: proposal, subviews: subviews)
        for (index, origin) in result.origins.enumerated() {
            subviews[index].place(
                at: CGPoint(x: bounds.minX + origin.x, y: bounds.minY + origin.y),
                proposal: .unspecified
            )
        }
    }

    private func arrange(proposal: ProposedViewSize, subviews: Subviews) -> (size: CGSize, origins: [CGPoint]) {
        let maxWidth = proposal.width ?? .infinity
        var origins: [CGPoint] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        var totalWidth: CGFloat = 0
        for subview in subviews {
            let size = subview.sizeThatFits(.unspecified)
            if x > 0, x + size.width > maxWidth {
                x = 0
                y += rowHeight + spacing
                rowHeight = 0
            }
            origins.append(CGPoint(x: x, y: y))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
            totalWidth = max(totalWidth, x - spacing)
        }
        return (CGSize(width: totalWidth, height: y + rowHeight), origins)
    }
}

// MARK: - 学期回忆录

/// P2 · 学期成局回忆录（Wrapped 式）：服务端事实聚合 + 匿名分享文案。
struct SemesterRecapView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @Environment(\.dismiss) private var dismiss
    @State private var recap: SemesterRecap?
    @State private var error: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if let recap {
                        content(recap)
                    } else if let error {
                        OMCard {
                            OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                                Task { await load() }
                            }
                        }
                    } else {
                        OMCard { OMG5StateView(state: .loading, message: "噜噜正在翻这学期的记录……") }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("学期回忆录")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } }
            }
        }
        .task { await load() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("profile-semester-recap")
    }

    @ViewBuilder private func content(_ recap: SemesterRecap) -> some View {
        VStack(spacing: 4) {
            LuluView(clip: recap.gatheringsCompleted > 0 ? .coreCelebrate : .homeIdle, placement: .empty)
            Text(recap.termLabel)
                .font(OMTheme.TypeToken.caption.weight(.semibold))
                .tracking(2)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, OMTheme.Spacing.s3)
        OMCard {
            HStack(spacing: 0) {
                statBlock("\(recap.gatheringsCompleted)", "成局")
                statBlock("\(recap.partnersMet)", "搭子")
                statBlock(recap.totalHours.formatted(.number.precision(.fractionLength(0...1))), "小时")
                statBlock("\(recap.recurrences)", "复局")
            }
        }
        if let partner = recap.topPartner, let name = partner.displayName {
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("handshake.png", size: .s44)
                    VStack(alignment: .leading, spacing: 2) {
                        OMTextRole.t3("最稳的搭子")
                        OMTextRole.foot("\(name) · 一起成了 \(partner.timesTogether) 局")
                    }
                    Spacer()
                }
            }
        }
        if !recap.topTypes.isEmpty {
            OMCard {
                OMTextRole.t3("这学期最常凑的")
                ForEach(recap.topTypes) { entry in
                    HStack {
                        Text(entry.gatheringType)
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        Spacer()
                        Text("\(entry.count) 局")
                            .font(OMTheme.TypeToken.mono(.footnote))
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                if let location = recap.topLocation {
                    OMTextRole.cap("最常去：\(location)").padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        if recap.gatheringsCompleted == 0 {
            OMCard {
                OMG5StateView(state: .empty, message: "这学期还没有完成的局；先从一张意图卡开始。")
            }
        }
        ShareLink(item: recap.shareText) {
            Label("分享这学期", systemImage: "square.and.arrow.up")
                .font(OMTheme.TypeToken.body.weight(.bold))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .frame(maxWidth: .infinity, minHeight: 52)
                .background(OMTheme.ColorToken.yolk)
                .clipShape(Capsule())
                .overlay { Capsule().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth) }
        }
        .padding(.top, OMTheme.Spacing.s2)
    }

    private func statBlock(_ value: String, _ label: String) -> some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.system(size: 28, weight: .heavy, design: .monospaced))
                .foregroundStyle(OMTheme.ColorToken.ink)
            Text(label)
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .frame(maxWidth: .infinity)
    }

    private func load() async {
        do {
            recap = try await environment.gatherings.semesterRecap()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}
