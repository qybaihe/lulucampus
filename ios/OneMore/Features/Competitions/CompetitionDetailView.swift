import SwiftUI

/// B12.1 · 赛事详情。视觉对齐 mobile-ios.html#/s/B12.1。
struct CompetitionDetailView: View {
    let id: String
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @Environment(\.openURL) private var openURL
    @State private var item: Competition?
    @State private var teams: [CompetitionTeam]?
    @State private var error: String?
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let item {
                    OMSticker("trophy.png", size: .s72)
                        .frame(maxWidth: .infinity)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.t1(item.name)
                        .frame(maxWidth: .infinity)
                        .multilineTextAlignment(.center)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.foot(
                        [
                            item.tasteFitLabel,
                            "\(item.recommendationLabel) · 已核验",
                            "队伍 \(item.teamSizeMin)–\(item.teamSizeMax) 人",
                        ]
                        .compactMap { $0 }
                        .joined(separator: " · ")
                    )
                        .frame(maxWidth: .infinity)
                        .multilineTextAlignment(.center)
                        .padding(.bottom, OMTheme.Spacing.s3)

                    if !item.tasteFitReasons.isEmpty || !item.recruitHints.isEmpty {
                        OMCard {
                            OMTextRole.t3("按你的兴趣画像")
                            ForEach(item.tasteFitReasons, id: \.self) { reason in
                                OMTextRole.foot(reason).padding(.top, OMTheme.Spacing.s2)
                            }
                            if !item.recruitHints.isEmpty {
                                OMTextRole.call("招什么样的人").padding(.top, OMTheme.Spacing.s3)
                                ForEach(item.recruitHints, id: \.self) { hint in
                                    OMTextRole.foot(hint).padding(.top, 4)
                                }
                            }
                        }
                    }

                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker(item.teamFormingSupported ? "round-table.png" : "chair-empty.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3(item.teamFormingSupported ? "支持赛事组队" : "仅找备赛搭子")
                                OMTextRole.foot("队伍范围 \(item.teamSizeMin)–\(item.teamSizeMax) 人")
                            }
                            Spacer()
                        }
                        if let deadline = item.registrationDeadline {
                            OMDivider()
                            HStack(spacing: 8) {
                                Image(om: .clock).font(.system(size: 14))
                                Text("报名截止 \(deadline.formatted(date: .long, time: .shortened))")
                            }
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        }
                        OMDivider()
                        OMTextRole.foot(item.registrationInstructions ?? "以官方页面为准")
                    }

                    if let rewards = item.rewards {
                        OMCard {
                            OMTextRole.t3("奖励与规则")
                            OMTextRole.foot(rewards).padding(.top, OMTheme.Spacing.s2)
                        }
                    }

                    if let teams, !teams.isEmpty {
                        OMCard {
                            HStack {
                                OMTextRole.t3("正在组队的队伍")
                                Spacer()
                                OMTextRole.foot("\(teams.count) 支")
                            }
                            ForEach(teams) { team in
                                OMDivider()
                                Button { router.push(.gathering(team.id)) } label: {
                                    VStack(alignment: .leading, spacing: 8) {
                                        HStack(spacing: 10) {
                                            OMLuluSeatStrip(
                                                filled: min(team.memberCount, team.targetSize),
                                                total: team.targetSize
                                            )
                                            Text("\(min(team.memberCount, team.targetSize))/\(team.targetSize)")
                                                .font(OMTheme.TypeToken.footnote.weight(.semibold))
                                                .foregroundStyle(OMTheme.ColorToken.ink)
                                            Spacer()
                                            Image(om: .arrow)
                                                .font(.system(size: 12, weight: .bold))
                                                .foregroundStyle(OMTheme.ColorToken.mist)
                                        }
                                        HStack(spacing: 6) {
                                            if let gap = team.gapDescription {
                                                OMChip(text: gap, kind: .gap)
                                            }
                                            if let startAt = team.startAt {
                                                OMChip(text: startAt.formatted(date: .abbreviated, time: .shortened), kind: .soft)
                                            }
                                        }
                                    }
                                    .padding(.vertical, 6)
                                }
                                .buttonStyle(.plain)
                                .accessibilityIdentifier("competition-team-\(team.id)")
                            }
                        }
                    }

                    OMButton(item.teamFormingSupported ? "找队友" : "找备赛搭子", systemIcon: "person.badge.plus") {
                        router.push(.intent(competitionID: item.id))
                    }
                    OMButton("打开官方报名页面", systemIcon: "safari", kind: .ghost) {
                        openURL(item.registrationUrl)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    ShareLink(item: item.registrationUrl, subject: Text(item.name), message: Text(item.name)) {
                        Label("系统分享赛事", systemImage: "square.and.arrow.up")
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(maxWidth: .infinity, minHeight: 38)
                            .clipShape(Capsule())
                            .overlay { Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                } else if let error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await load() }
                        }
                    }
                } else {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B12.1-competition-detail")
        .navigationBarTitleDisplayMode(.inline)
    }
    private func load() async {
        do {
            item = try await environment.api.get("/competitions/\(id)")
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
        teams = await environment.competitions.teams(competitionID: id)
    }
}
