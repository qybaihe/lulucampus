import SwiftUI

/// B12.2 · 赛事牌桌：正在招人的队伍列表（匿名席位 + 缺口）。
struct CompetitionTeamBoardView: View {
    let competitionID: String
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var item: Competition?
    @State private var teams: [CompetitionTeam]?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(
                    eyebrow: "赛事牌桌",
                    title: recruitingTitle,
                    lulu: .confirmGather
                )
                .padding(.bottom, OMTheme.Spacing.s3)

                if let error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await load() }
                        }
                    }
                } else if let teams {
                    if teams.isEmpty {
                        OMCard {
                            OMG5StateView(
                                state: .empty,
                                message: "暂时还没有队伍在招人。你可以自己组一队，发布后会出现在这里。"
                            )
                        }
                    } else {
                        ForEach(teams) { team in
                            Button {
                                router.push(.competitionTeam(competitionID: competitionID, teamID: team.id))
                            } label: {
                                OMCard(hotSeat: item.map { CompetitionSpotlight.isHotTeam($0, team) } ?? false) {
                                    CompetitionTeamSummary(team: team, competition: item)
                                }
                            }
                            .buttonStyle(.plain)
                            .accessibilityIdentifier("competition-team-\(team.id)")
                        }
                    }
                } else {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                }

                OMButton("自己组一队", systemIcon: "person.badge.plus") {
                    router.push(.intent(competitionID: competitionID))
                }
                .padding(.top, OMTheme.Spacing.s3)
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await load() }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-B12.2-table")
        .navigationBarTitleDisplayMode(.inline)
    }

    private var recruitingTitle: String {
        guard let teams else { return "正在招人" }
        if teams.isEmpty { return "还没有人在招" }
        return "有 \(teams.count) 支队伍正在招人"
    }

    private func load() async {
        do {
            async let detail: Competition = environment.api.get("/competitions/\(competitionID)")
            async let listed = environment.competitions.teams(competitionID: competitionID)
            item = try await detail
            teams = await listed ?? []
            error = nil
        } catch {
            self.error = error.localizedDescription
            teams = await environment.competitions.teams(competitionID: competitionID)
        }
    }
}

/// 单支招募中队伍的匿名详情：几/几、已有角色、还缺什么。
struct CompetitionTeamDetailView: View {
    let competitionID: String
    let teamID: String
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var item: Competition?
    @State private var team: CompetitionTeam?
    @State private var error: String?

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                if let team {
                    OMSticker("round-table.png", size: .s72)
                        .frame(maxWidth: .infinity)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.t1(team.title)
                        .frame(maxWidth: .infinity)
                        .multilineTextAlignment(.center)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMTextRole.foot("\(team.filled)/\(team.targetSize) · \(team.sizeRangeLabel) · 正在招人")
                        .frame(maxWidth: .infinity)
                        .padding(.bottom, OMTheme.Spacing.s3)

                    OMCard(hotSeat: item.map { CompetitionSpotlight.isHotTeam($0, team) } ?? false) {
                        HStack(spacing: 10) {
                            OMLuluSeatStrip(filled: team.filled, total: team.targetSize)
                            Text("\(team.filled)/\(team.targetSize)")
                                .font(OMTheme.TypeToken.title1)
                                .foregroundStyle(OMTheme.ColorToken.ink)
                            Spacer()
                        }
                        if let gap = team.gapDescription {
                            OMChip(text: gap, kind: .gap)
                                .padding(.top, OMTheme.Spacing.s3)
                        }
                    }

                    if let filled = team.filledRoles, !filled.isEmpty {
                        OMCard {
                            OMTextRole.t3("桌上已经有谁")
                            HStack(spacing: 6) {
                                ForEach(filled, id: \.self) { role in
                                    OMChip(text: CapabilityLabel.displayName(for: role), kind: .soft)
                                }
                            }
                            .padding(.top, OMTheme.Spacing.s2)
                            if let highlights = team.rosterHighlights, !highlights.isEmpty {
                                HStack(spacing: 6) {
                                    ForEach(highlights, id: \.self) { highlight in
                                        OMChip(text: highlight, kind: .standard)
                                    }
                                }
                                .padding(.top, OMTheme.Spacing.s2)
                            }
                        }
                    }

                    if !team.resolvedMissingRoles.isEmpty {
                        OMCard {
                            OMTextRole.t3("还缺这些")
                            HStack(spacing: 6) {
                                ForEach(team.resolvedMissingRoles, id: \.self) { role in
                                    OMChip(text: CapabilityLabel.displayName(for: role), kind: .gap)
                                }
                            }
                            .padding(.top, OMTheme.Spacing.s2)
                        }
                    }

                    if let goal = team.goal, !goal.isEmpty {
                        OMCard {
                            OMTextRole.t3("这支队伍在找什么")
                            OMTextRole.foot(goal).padding(.top, OMTheme.Spacing.s2)
                        }
                    }

                    OMCard {
                        if let campus = team.campus, let location = team.location {
                            HStack(spacing: 8) {
                                Image(om: .pin).font(.system(size: 14))
                                Text("\(campus) · \(location)")
                            }
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        }
                        if let startAt = team.startAt {
                            OMDivider()
                            HStack(spacing: 8) {
                                Image(om: .clock).font(.system(size: 14))
                                Text(startAt.formatted(date: .abbreviated, time: .shortened))
                            }
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        }
                    }

                    OMButton("想加入这支队伍", systemIcon: "person.badge.plus") {
                        router.push(.gathering(team.id))
                    }
                    OMButton("看其他招人队伍", kind: .ghost) {
                        router.push(.competitionTable(competitionID))
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
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-B12.2-team-detail")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func load() async {
        do {
            async let listed: Competition = environment.api.get("/competitions/\(competitionID)")
            async let detail = environment.competitions.team(competitionID: competitionID, teamID: teamID)
            item = try await listed
            team = try await detail
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct CompetitionTeamSummary: View {
    let team: CompetitionTeam
    var competition: Competition? = nil

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 10) {
                OMLuluSeatStrip(filled: team.filled, total: team.targetSize)
                Text("\(team.filled)/\(team.targetSize)")
                    .font(OMTheme.TypeToken.footnote.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                if team.minSize != nil {
                    Text(team.sizeRangeLabel)
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                Spacer()
                Image(om: .arrow)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            OMTextRole.t3(team.title)
            HStack(spacing: 6) {
                if let competition, CompetitionSpotlight.isHotTeam(competition, team), team.gapDescription == nil {
                    OMChip(text: "正好差一个", kind: .gap)
                }
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
}
