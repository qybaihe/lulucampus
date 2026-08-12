import SwiftUI

/// C3 is a server-triggered recovery state.  It renders only the viewer's
/// trust facts and keeps the rejected task in the typed navigation stack.
struct TrustRequirementView: View {
    let context: TrustRequirementContext

    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var trust: TrustProgress?
    @State private var error: String?
    @State private var loading = false

    private var requirementSatisfied: Bool {
        guard let trust else { return false }
        return Self.levelRank(trust.level) >= Self.levelRank(context.requiredLevel)
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "信任门槛", title: "先积累一次可靠履约", lulu: .coreCare)

                OMCard {
                    HStack(spacing: 10) {
                        Image(om: .shield)
                            .font(.system(size: 17))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(width: 38, height: 38)
                            .background(OMTheme.ColorToken.gapSoft)
                            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3("这次操作由服务端暂缓")
                            OMTextRole.foot(context.serverMessage)
                        }
                        Spacer()
                    }
                    HStack(spacing: 12) {
                        levelMetric(
                            title: "当前",
                            value: trust?.level ?? "—",
                            highlighted: false,
                            identifier: "trust-current-level"
                        )
                        Image(om: .arrow)
                            .foregroundStyle(OMTheme.ColorToken.sage)
                        levelMetric(
                            title: "要求",
                            value: context.requiredLevel,
                            highlighted: true,
                            identifier: "trust-required-level"
                        )
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                    Text("能力：\(context.capabilityTitle)")
                        .font(OMTheme.TypeToken.footnote.weight(.bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.top, OMTheme.Spacing.s3)
                        .accessibilityIdentifier("trust-capability")
                }

                if loading && trust == nil {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if let trust {
                    if requirementSatisfied {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("medal.png", size: .s44)
                                VStack(alignment: .leading, spacing: 2) {
                                    OMTextRole.t3("服务端已确认门槛满足")
                                    OMTextRole.foot("原任务仍保留，可从这里继续，不必重新寻找。")
                                }
                                Spacer()
                            }
                        }
                        OMButton(context.recoveryTarget.title, systemIcon: "arrow.uturn.forward") {
                            router.path = [context.recoveryTarget.route]
                        }
                        .padding(.top, OMTheme.Spacing.s2)
                        .accessibilityIdentifier("trust-resume-original")
                    } else {
                        OMSection(title: "先从低风险公开局开始")
                        OMCard {
                            HStack {
                                OMTextRole.t3(
                                    trust.nextLevel.map { "升到 \($0) 还需" } ?? "只展示你自己的升级条件"
                                )
                                Spacer()
                                if trust.nextLevel != nil {
                                    Text("\(Int((trust.overallProgress * 100).rounded()))%")
                                        .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                                        .foregroundStyle(OMTheme.ColorToken.ink)
                                }
                            }
                            if trust.nextLevel != nil {
                                OMProgressBar(value: trust.overallProgress)
                                    .padding(.top, OMTheme.Spacing.s2)
                            }
                            let rows = trust.conditions.isEmpty
                                ? trust.gaps.map { ($0, false as Bool, Optional<String>.none) }
                                : trust.conditions.map { ($0.label, $0.met, $0.detail) }
                            if !rows.isEmpty {
                                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                                    HStack(alignment: .top, spacing: 8) {
                                        Image(systemName: row.1 ? "checkmark.circle.fill" : "circle")
                                            .font(.system(size: 13))
                                            .foregroundStyle(row.1 ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                                        VStack(alignment: .leading, spacing: 2) {
                                            Text(row.0)
                                                .font(OMTheme.TypeToken.callout)
                                                .foregroundStyle(OMTheme.ColorToken.ink)
                                            if !row.1, let detail = row.2, detail != row.0 {
                                                Text(detail)
                                                    .font(OMTheme.TypeToken.footnote)
                                                    .foregroundStyle(OMTheme.ColorToken.mist)
                                            }
                                        }
                                    }
                                    .padding(.top, OMTheme.Spacing.s2)
                                    .accessibilityIdentifier("trust-gap-item")
                                }
                            }
                        }
                        OMButton("去参加低风险公开局", systemIcon: "person.3") {
                            router.push(.publicGatherings)
                        }
                        .padding(.top, OMTheme.Spacing.s2)
                        .accessibilityIdentifier("trust-open-low-risk")
                    }

                    OMButton(loading ? "正在刷新…" : "刷新信任进度", kind: .ghost, loading: loading) {
                        Task { await load() }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    .accessibilityIdentifier("trust-refresh")

                    OMButton("查看完整 T0–T4 说明", kind: .text, small: true, fillsWidth: false) {
                        router.push(.trust)
                    }
                } else if let error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await load() }
                        }
                    }
                }

            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await load() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-C3-trust-requirement")
    }

    private func levelMetric(title: String, value: String, highlighted: Bool, identifier: String) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(title)
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
            Text(value)
                .font(.system(size: 34, weight: .heavy, design: .monospaced))
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.horizontal, highlighted ? 8 : 0)
                .padding(.vertical, highlighted ? 2 : 0)
                .background(highlighted ? OMTheme.ColorToken.yolk : .clear)
                .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier(identifier)
    }

    private func load() async {
        guard !loading else { return }
        loading = true
        defer { loading = false }
        do {
            trust = try await environment.social.trust()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private static func levelRank(_ value: String) -> Int {
        Int(value.dropFirst()) ?? -1
    }
}
