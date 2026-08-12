import SwiftUI

/// M1 · 我（Tab 根）。视觉对齐 mobile-ios.html#/s/M1。
struct ProfileView: View {
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @State private var facts: IdentityFacts?
    @State private var profile: UserProfilePayload?
    @State private var factsError: String?
    @State private var signOutError: String?
    @State private var showsRecap = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "\(AppBrand.displayName) · 我")
                if let facts {
                    OMCard {
                        HStack(spacing: 14) {
                            LuluView(clip: .homeIdle, placement: .avatar)
                                .frame(width: 62, height: 62)
                                .background {
                                    Circle().fill(OMTheme.ColorToken.gapSoft)
                                }
                                .clipShape(Circle())
                                .accessibilityHidden(true)
                            VStack(alignment: .leading, spacing: 3) {
                                OMTextRole.t2(facts.displayName ?? "已认证同学")
                                OMTextRole.foot([facts.campus, facts.major].compactMap { $0 }.joined(separator: " · "))
                            }
                            Spacer()
                        }
                    }
                } else if let factsError {
                    OMCard {
                        OMG5StateView(state: .networkError, message: factsError, actionTitle: "重试") {
                            Task { await loadFacts() }
                        }
                    }
                } else {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                }

                if let taste = profile?.tasteProfile, taste.primaryTag != nil || (taste.summary?.isEmpty == false) {
                    OMSection(title: "我的兴趣画像")
                    OMCard {
                        if let primary = taste.primaryTag {
                            Text(primary.label)
                                .font(OMTheme.TypeToken.callout.weight(.bold))
                        }
                        if let tags = taste.interestTags, !tags.isEmpty {
                            Text(tags.prefix(5).joined(separator: " · "))
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                                .padding(.top, OMTheme.Spacing.s2)
                        } else if let secondary = taste.secondaryTags, !secondary.isEmpty {
                            Text(secondary.prefix(4).joined(separator: " · "))
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        if let summary = taste.summary, !summary.isEmpty {
                            OMTextRole.foot(summary).padding(.top, OMTheme.Spacing.s2)
                        }
                        OMButton("管理 / 刷新画像", kind: .ghost, small: true, fillsWidth: false) {
                            router.push(.tasteImport)
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                    }
                    .accessibilityIdentifier("profile-taste-summary")
                }

                OMSection(title: "局与关系")
                OMCard(tight: true) {
                    OMRow(sticker: "table-people.png", title: "我的局", onTap: { router.push(.myGatherings) })
                    OMRow(sticker: "handshake.png", title: "搭子关系", onTap: { router.push(.relations) })
                    OMRow(sticker: "table-plus.png", title: "直接发起局", onTap: { router.push(.initiateGathering) })
                    OMRow(sticker: "trophy.png", title: "学期回忆录", onTap: { showsRecap = true })
                        .accessibilityIdentifier("profile-semester-recap-entry")
                }

                OMSection(title: "画像与信任")
                OMCard(tight: true) {
                    OMRow(sticker: "id-card.png", title: "画像与能力", onTap: { router.push(.formal(.m2)) })
                    OMRow(sticker: "medal.png", title: "信任进度", onTap: { router.push(.trust) })
                    OMRow(sticker: "key.png", title: "授权管理", onTap: { router.push(.grants) })
                    OMRow(sticker: "sparkle-wand.png", title: "抖音兴趣画像", onTap: { router.push(.tasteImport) })
                        .accessibilityIdentifier("profile-taste-import")
                }

                OMSection(title: "隐私与安全")
                OMCard(tight: true) {
                    OMRow(sticker: "shield-check.png", title: "隐私与安全", onTap: { router.push(.formal(.m5)) })
                    OMRow(sticker: "sliders.png", title: "匹配偏好", onTap: { router.push(.matchingPreferences) })
                    OMRow(sticker: "block-sign.png", title: "黑名单", onTap: { router.push(.blocks) })
                    OMRow(sticker: "flag.png", title: "历史局安全与举报", onTap: { router.push(.departedSafety) })
                    OMRow(sticker: "megaphone.png", title: "信任申诉", onTap: { router.push(.formal(.m9)) })
                }

                OMSection(title: "偏好与数据")
                OMCard(tight: true) {
                    OMRow(sticker: "bell.png", title: "通知与日历", onTap: { router.push(.formal(.m7)) })
                    OMRow(sticker: "clipboard-whistle.png", title: "主理人控制台", onTap: { router.push(.organizer) })
                    OMRow(sticker: "box-export.png", title: "数据导出与注销", onTap: { router.push(.accountData) })
                    OMRow(icon: .spark, title: "重新查看新手引导", onTap: {
                        Task {
                            await environment.session.resetOnboarding()
                            router.selectedTab = .today
                            router.path = [.onboarding("A1")]
                        }
                    })
                    .accessibilityIdentifier("profile-reset-onboarding")
                    }

                    OMCard(tight: true) {
                        OMRow(icon: .exit, title: "退出登录", onTap: {
                            Task {
                                do {
                                    try await environment.session.signOut()
                                    signOutError = nil
                                } catch {
                                    signOutError = "退出前需先注销通知设备：\(error.localizedDescription)"
                                }
                            }
                        })
                    }

                if let error = environment.referenceDataError {
                    OMCard { OMG5StateView(state: .networkError, message: "离线数据整包已拒绝：\(error)") }
                }
                if let signOutError {
                    OMCard { OMG5StateView(state: .networkError, message: signOutError) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await loadFacts() }
        .sheet(isPresented: $showsRecap) { SemesterRecapView() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M1-profile")
    }

    private func loadFacts() async {
        do {
            async let factsTask = environment.identity.facts()
            async let profileTask = environment.identity.profile()
            facts = try await factsTask
            profile = try? await profileTask
            factsError = nil
        } catch {
            factsError = error.localizedDescription
        }
    }
}
