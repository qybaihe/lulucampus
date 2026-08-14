import SwiftUI

@MainActor
final class PrivacySettingsViewModel: ObservableObject {
    @Published var value: SocialPreferences?
    @Published var loading = true
    @Published var saving = false
    @Published var error: String?
    private let repository: IdentityRepository

    init(repository: IdentityRepository) { self.repository = repository }
    func load() async {
        loading = true
        defer { loading = false }
        do { value = try await repository.privacy(); error = nil }
        catch {
            if error.isCancellation { return }
            self.error = error.localizedDescription
        }
    }
    func save() async {
        guard let value, !saving else { return }
        saving = true
        defer { saving = false }
        do {
            self.value = try await repository.updatePrivacy(value)
            error = nil
            NotificationCenter.default.post(name: .oneMoreSocialPreferencesDidChange, object: nil)
        } catch {
            if error.isCancellation { return }
            self.error = error.localizedDescription
        }
    }
    func saveSocial(enabled: Bool) async {
        guard !saving else { return }
        saving = true
        defer { saving = false }
        do {
            self.value = try await repository.setSocialEnabled(enabled)
            error = nil
            NotificationCenter.default.post(name: .oneMoreSocialPreferencesDidChange, object: nil)
        } catch {
            if error.isCancellation { return }
            value?.socialEnabled = !enabled
            value?.courseMatchingEnabled = !enabled
            self.error = error.localizedDescription
        }
    }
}

/// M5 · 隐私与安全
struct PrivacySettingsView: View {
    @StateObject private var model: PrivacySettingsViewModel
    init(repository: IdentityRepository) {
        _model = StateObject(wrappedValue: PrivacySettingsViewModel(repository: repository))
    }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(title: "隐私与安全", lulu: .coreCare)
                if model.value != nil {
                    OMSection(title: "进入匹配")
                    OMCard(tight: true) {
                        OMRow(sticker: "shield-check.png", title: "社交总开关", toggle: socialEnabledBinding)
                        OMRow(sticker: "books-stack.png", title: "允许基于课程匹配", toggle: binding(\.courseMatchingEnabled))
                    }
                    OMSection(title: "见面边界")
                    OMCard {
                        OMTextRole.foot("身份公开时机")
                        OMSeg(
                            items: ["after_confirmed", "after_full"],
                            label: { $0 == "after_confirmed" ? "全员确认后" : "满员后" },
                            selection: binding(\.identityDisclosure)
                        )
                        .padding(.top, OMTheme.Spacing.s2)
                    }
                    OMCard(tight: true) {
                        OMRow(sticker: "sliders.png", title: "只匹配同性成员", toggle: binding(\.sameGenderOnly))
                    }
                    OMCard(tight: true) {
                        OMStepperRow(title: "最低成局人数", value: binding(\.minimumGroupSize), range: 2...20)
                    }

                    OMSection(title: "场景敏感度")
                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker("seminar-room-sign.png", size: .s44)
                            OMTextRole.t3("图书馆自习区 / 健身房器械区现场禁言")
                            Spacer()
                        }
                    }

                    if let error = model.error {
                        Text(error)
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .padding(.top, OMTheme.Spacing.s3)
                    }
                    OMButton(model.saving ? "保存中…" : "保存隐私设置", icon: .shield, loading: model.saving) {
                        Task { await model.save() }
                    }
                    .padding(.top, OMTheme.Spacing.s4)
                } else if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M5-privacy")
    }

    private var socialEnabledBinding: Binding<Bool> {
        Binding {
            model.value?.socialEnabled ?? false
        } set: { enabled in
            model.value?.socialEnabled = enabled
            model.value?.courseMatchingEnabled = enabled
            Task { await model.saveSocial(enabled: enabled) }
        }
    }

    private func binding<Value>(
        _ path: WritableKeyPath<SocialPreferences, Value>
    ) -> Binding<Value> {
        Binding {
            guard let value = model.value else { fatalError("privacy not loaded") }
            return value[keyPath: path]
        } set: { model.value?[keyPath: path] = $0 }
    }
}

/// M3 · 信任进度（仅展示自己的等级、下一级条件与权益；不展示他人等级 / 技术能力键）
struct TrustView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var trust: TrustProgress?
    @State private var error: String?
    @State private var showGuide = false
    @State private var loading = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "信任等级", title: "信任进度", lulu: .coreCelebrate)
                if let trust {
                    heroCard(trust)
                    if trust.nextLevel != nil {
                        upgradeProgressCard(trust)
                    } else {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("medal.png", size: .s44)
                                VStack(alignment: .leading, spacing: 2) {
                                    OMTextRole.t3("已达最高等级")
                                    OMTextRole.foot("T4 校园主理人权益已全部解锁。")
                                }
                                Spacer()
                            }
                        }
                        .accessibilityIdentifier("trust-max-level")
                    }
                    if !trust.currentBenefits.isEmpty {
                        benefitsCard(title: "本级已解锁", benefits: trust.currentBenefits, muted: false)
                            .accessibilityIdentifier("trust-current-benefits")
                    }
                    if !trust.nextBenefits.isEmpty {
                        benefitsCard(
                            title: trust.nextLevelName.map { "升到 \($0) 将解锁" } ?? "下一级将解锁",
                            benefits: trust.nextBenefits,
                            muted: true
                        )
                        .accessibilityIdentifier("trust-next-benefits")
                    }
                    OMButton("查看升级说明 · T0–T4 标准", kind: .ghost) {
                        showGuide = true
                    }
                    .accessibilityIdentifier("trust-open-guide")
                    OMButton("查看信任申诉", kind: .ghost) { router.push(.formal(.m9)) }
                    OMButton("去看能马上参加的公开局", systemIcon: "person.3") {
                        router.push(.publicGatherings)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    .accessibilityIdentifier("trust-open-low-risk-gatherings")
                    OMButton(loading ? "正在刷新…" : "刷新信任进度", kind: .text, small: true, fillsWidth: false) {
                        Task { await load() }
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
        .sheet(isPresented: $showGuide) {
            TrustLevelGuideSheet(guide: trust?.levelGuide ?? [], currentLevel: trust?.level)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-M3-trust")
    }

    @ViewBuilder
    private func heroCard(_ trust: TrustProgress) -> some View {
        OMCard {
            HStack(spacing: 14) {
                OMSticker(Self.medalSticker(for: trust.level), size: .s56)
                VStack(alignment: .leading, spacing: 3) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(trust.level)
                            .font(OMTheme.TypeToken.mono(.title2, weight: .heavy))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .accessibilityIdentifier("trust-current-level")
                        OMTextRole.t2(trust.levelName)
                    }
                    if let narrative = trust.levelNarrative, !narrative.isEmpty {
                        OMTextRole.foot(narrative)
                    } else if let next = trust.nextLevel {
                        let name = trust.nextLevelName.map { " · \($0)" } ?? ""
                        OMTextRole.foot("下一等级 \(next)\(name)")
                    } else {
                        OMTextRole.foot("当前最高等级")
                    }
                }
                Spacer(minLength: 0)
            }
            if let observation = trust.observation, observation["until"] != nil {
                OMDivider()
                HStack(spacing: 8) {
                    Image(om: .shield).font(.system(size: 13))
                    Text("观察期内等级暂时冻结，到期后按履约事实重新计算")
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                }
                .padding(.top, 4)
                .accessibilityIdentifier("trust-observation-banner")
            }
        }
    }

    @ViewBuilder
    private func upgradeProgressCard(_ trust: TrustProgress) -> some View {
        let nextCode = trust.nextLevel ?? ""
        let nextName = trust.nextLevelName ?? nextCode
        OMSection(title: "升到下一级")
        OMCard {
            HStack(alignment: .firstTextBaseline) {
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(nextCode) · \(nextName)")
                        .font(OMTheme.TypeToken.callout.weight(.bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    OMTextRole.foot(overallCaption(trust))
                }
                Spacer()
                Text("\(Int((trust.overallProgress * 100).rounded()))%")
                    .font(OMTheme.TypeToken.mono(.title3, weight: .heavy))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .accessibilityIdentifier("trust-overall-progress")
            }
            OMProgressBar(value: trust.overallProgress)
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("trust-overall-progress-bar")

            let conditions = displayConditions(trust)
            if !conditions.isEmpty {
                ForEach(conditions) { condition in
                    conditionRow(condition)
                        .padding(.top, OMTheme.Spacing.s3)
                        .accessibilityIdentifier("trust-condition-\(condition.key)")
                }
            }
        }
        .accessibilityIdentifier("trust-upgrade-card")
    }

    private func conditionRow(_ condition: TrustProgress.Condition) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Image(systemName: condition.met ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(condition.met ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                Text(condition.label)
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer(minLength: 8)
                Text(condition.metricText)
                    .font(OMTheme.TypeToken.mono(.caption, weight: .bold))
                    .foregroundStyle(condition.met ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
            }
            if condition.hasMetric {
                OMProgressBar(value: condition.ratio)
            } else if !condition.met, let detail = condition.detail, detail != condition.label {
                Text(detail)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.leading, 23)
            }
        }
    }

    @ViewBuilder
    private func benefitsCard(title: String, benefits: [String], muted: Bool) -> some View {
        OMSection(title: title)
        OMCard {
            ForEach(Array(benefits.enumerated()), id: \.offset) { index, benefit in
                HStack(alignment: .top, spacing: 8) {
                    Image(systemName: muted ? "lock.open" : "sparkles")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(muted ? OMTheme.ColorToken.sage : OMTheme.ColorToken.ink)
                        .frame(width: 16)
                        .padding(.top, 2)
                    Text(benefit)
                        .font(OMTheme.TypeToken.callout)
                        .foregroundStyle(muted ? OMTheme.ColorToken.mist : OMTheme.ColorToken.ink)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
                .padding(.top, index == 0 ? 0 : OMTheme.Spacing.s2)
            }
        }
    }

    /// Prefer structured conditions; fall back to gaps for older payloads.
    private func displayConditions(_ trust: TrustProgress) -> [TrustProgress.Condition] {
        if !trust.conditions.isEmpty { return trust.conditions }
        if !trust.nextLevelProgress.isEmpty {
            return trust.nextLevelProgress.map { metric in
                TrustProgress.Condition(
                    key: metric.key,
                    label: metric.label,
                    met: metric.current >= metric.required,
                    current: metric.current,
                    required: metric.required,
                    unit: metric.unit,
                    detail: metric.current >= metric.required
                        ? nil
                        : "还差 \(max(0, Int(metric.required - metric.current))) \(metric.unit)"
                )
            }
        }
        return trust.gaps.enumerated().map { index, gap in
            TrustProgress.Condition(
                key: "gap-\(index)",
                label: gap,
                met: false,
                detail: gap
            )
        }
    }

    private func overallCaption(_ trust: TrustProgress) -> String {
        let remaining = trust.conditions.filter { !$0.met }.count
        if remaining == 0, !trust.conditions.isEmpty {
            return "条件已齐，刷新后由服务端确认升级"
        }
        if remaining > 0 {
            return "还差 \(remaining) 项条件"
        }
        if let first = trust.gaps.first {
            return first
        }
        return "按履约事实自动计算，无需申请"
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

    static func medalSticker(for level: String) -> String {
        switch level {
        case "T0": "trust-t0.png"
        case "T1": "trust-t1.png"
        case "T2": "trust-t2.png"
        case "T3": "trust-t3.png"
        case "T4": "trust-t4.png"
        default: "trust-t0.png"
        }
    }
}

/// 升级说明：完整 T0–T4 达标标准与权益（不在主路径罗列技术能力键）
struct TrustLevelGuideSheet: View {
    let guide: [TrustProgress.LevelGuideItem]
    var currentLevel: String? = nil
    @Environment(\.dismiss) private var dismiss

    private var items: [TrustProgress.LevelGuideItem] {
        if !guide.isEmpty { return guide }
        return Self.fallbackGuide(currentLevel: currentLevel)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "升级文档", title: "T0–T4 标准说明", lulu: .coreCare)
                    ForEach(items) { item in
                        OMCard {
                            HStack(alignment: .top, spacing: 12) {
                                OMSticker(TrustView.medalSticker(for: item.level), size: .s44)
                                    .opacity(item.isReached ? 1 : 0.45)
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack(spacing: 6) {
                                        Text(item.level)
                                            .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                                            .foregroundStyle(item.isCurrent ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                                        OMTextRole.t3(item.name)
                                        if item.isCurrent {
                                            OMChip(text: "当前", kind: .solid)
                                        }
                                    }
                                    OMTextRole.foot("如何达到：\(item.how)")
                                    if !item.benefits.isEmpty {
                                        ForEach(item.benefits, id: \.self) { benefit in
                                            HStack(alignment: .top, spacing: 6) {
                                                Text("·")
                                                    .foregroundStyle(OMTheme.ColorToken.sage)
                                                Text(benefit)
                                                    .font(OMTheme.TypeToken.footnote)
                                                    .foregroundStyle(OMTheme.ColorToken.ink)
                                            }
                                            .padding(.top, 2)
                                        }
                                    }
                                }
                                Spacer(minLength: 0)
                                Image(systemName: item.isReached ? "checkmark.seal.fill" : "lock.fill")
                                    .foregroundStyle(item.isReached ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                            }
                        }
                        .accessibilityIdentifier("trust-guide-\(item.level)")
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("完成") { dismiss() }
                }
            }
        }
        .presentationDetents([.large])
        .accessibilityIdentifier("sheet-trust-level-guide")
    }

    private static func fallbackGuide(currentLevel: String?) -> [TrustProgress.LevelGuideItem] {
        let rank: (String) -> Int = { Int($0.dropFirst()) ?? -1 }
        let current = currentLevel ?? "T0"
        let rows: [(String, String, String, [String])] = [
            ("T0", "访客", "下载 App 即可进入", ["浏览公开内容与校园资讯"]),
            ("T1", "已认证同学", "完成统一身份认证与画像初始化", ["参加 3 人及以上的低风险公开局", "创建意图卡", "同课破冰、DDL 冲刺"]),
            ("T2", "靠谱同学", "完成 3 次有效成局 · 准时确认率 ≥ 80% · 近 30 天无临期爽约 · 无有效举报", ["比赛 / 项目组队池", "自行发起公开局", "双人局与跨院系匹配", "校园预约代理"]),
            ("T3", "组局者", "累计 10 次有效成局 · ≥ 3 次本人发起 · 复局 ≥ 2 次 · 爽约率 < 10%", ["长期共同目标", "周期性固定局", "6 人以上大组", "补位快线"]),
            ("T4", "校园主理人", "经社团 / 院系 / 平台核验的主理人认证", ["官方局", "主理人管理台与模板"]),
        ]
        return rows.map { level, name, how, benefits in
            TrustProgress.LevelGuideItem(
                level: level,
                name: name,
                how: how,
                benefits: benefits,
                isCurrent: level == current,
                isReached: rank(level) <= rank(current)
            )
        }
    }
}

@MainActor
final class TrustAppealsViewModel: ObservableObject {
    @Published var appeals: [TrustAppeal] = []
    @Published var reason = ""
    @Published var loading = true
    @Published var submitting = false
    @Published var error: String?
    private let repository: SocialRepository

    init(repository: SocialRepository) { self.repository = repository }
    func load() async {
        loading = true; defer { loading = false }
        do { appeals = try await repository.appeals(); error = nil }
        catch { self.error = error.localizedDescription }
    }
    func submit() async {
        let value = reason.trimmingCharacters(in: .whitespacesAndNewlines)
        guard value.count >= 10, !submitting else { return }
        submitting = true; defer { submitting = false }
        do { _ = try await repository.submitAppeal(reason: value); reason = ""; appeals = try await repository.appeals(); error = nil }
        catch { self.error = error.localizedDescription }
    }
}

/// M9 · 信任申诉
struct TrustAppealsView: View {
    @StateObject private var model: TrustAppealsViewModel
    init(repository: SocialRepository) { _model = StateObject(wrappedValue: TrustAppealsViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "信任复核", title: "信任申诉", lulu: .coreCare)
                OMCard {
                    OMTextRole.t3("申诉原因")
                    TextField("至少 10 个字，说明需要复核的事实", text: $model.reason, axis: .vertical)
                        .omInputStyle(multiline: true)
                        .padding(.top, OMTheme.Spacing.s3)
                        .accessibilityIdentifier("trust-appeal-reason")
                }
                OMButton("提交申诉", loading: model.submitting, disabledReason: model.reason.trimmingCharacters(in: .whitespacesAndNewlines).count < 10 ? "请至少填写 10 个字" : nil) {
                    Task { await model.submit() }
                }
                if model.loading {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                } else if model.appeals.isEmpty {
                    OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                }
                ForEach(model.appeals) { appeal in
                    OMCard {
                        HStack {
                            OMChip(text: appeal.status, kind: .soft)
                            Spacer()
                            Text(appeal.updatedAt.formatted(date: .abbreviated, time: .shortened))
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        OMTextRole.call(appeal.reason).padding(.top, OMTheme.Spacing.s2)
                        if let result = appeal.result {
                            OMTextRole.foot("处理结果：\(result)").padding(.top, OMTheme.Spacing.s2)
                        }
                    }
                }
                if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M9-appeals")
    }
}

@MainActor final class NotificationPreferencesViewModel: ObservableObject {
    @Published var value: NotificationPreferences?
    @Published var inbox: [InboxNotification] = []
    @Published var error: String?
    @Published var saving = false
    let repository: SocialRepository
    init(repository: SocialRepository) { self.repository = repository }
    func load() async {
        do {
            value = try await repository.notificationPreferences()
            error = nil
        } catch {
            self.error = error.localizedDescription
            return
        }
        do {
            inbox = try await repository.notifications()
        } catch {
            if self.error == nil { self.error = error.localizedDescription }
        }
    }
    @discardableResult
    func save() async -> NotificationPreferences? {
        guard let value, !saving else { return nil }
        saving = true
        defer { saving = false }
        do {
            let saved = try await repository.updatePreferences(value)
            self.value = saved
            error = nil
            return saved
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }

    var visibleInbox: [InboxNotification] {
        guard let categories = value?.categories else { return inbox }
        return inbox.filter { item in
            switch item.resolvedCategory {
            case "schedule_reminders": categories.scheduleReminders
            case "gathering_updates": categories.gatheringUpdates
            case "chat_messages": categories.chatMessages
            case "action_updates": categories.actionUpdates
            case "trust_updates": categories.trustUpdates
            case "competition_deadlines": categories.competitionDeadlines
            default: categories.gatheringUpdates
            }
        }
    }
}

/// M7 · 通知与日历
struct NotificationPreferencesView: View {
    @StateObject private var model: NotificationPreferencesViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    init(repository: SocialRepository) { _model = StateObject(wrappedValue: NotificationPreferencesViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "提醒与日历", title: "通知", lulu: .homeListening)
                if model.value != nil {
                    OMCard(tight: true) {
                        OMRow(sticker: "bell.png", title: "业务通知总开关", toggle: binding(\.overallEnabled))
                        OMRow(sticker: "desk-calendar.png", title: "执行成功后同步日历", toggle: binding(\.calendarSyncEnabled), showsDivider: false)
                    }
                    OMSection(title: "看哪些提醒")
                    OMCard(tight: true) {
                        OMRow(icon: .flag, title: "成局", sub: "凑局、确认、改约", toggle: category(\.gatheringUpdates))
                        OMRow(icon: .cal, title: "日程", sub: "上课、作业截止", toggle: category(\.scheduleReminders))
                        OMRow(icon: .chat, title: "消息", toggle: category(\.chatMessages))
                        OMRow(icon: .doc, title: "行动执行", toggle: category(\.actionUpdates))
                        OMRow(icon: .shield, title: "信任", toggle: category(\.trustUpdates))
                        OMRow(icon: .trophy, title: "赛事截止", toggle: category(\.competitionDeadlines), showsDivider: false)
                    }
                    OMNote(text: "关掉的分类不会推送，也不会出现在下面的列表里。保存后同步到其他设备。")
                        .padding(.top, OMTheme.Spacing.s3)
                    OMSection(title: "最近提醒")
                    if model.visibleInbox.isEmpty {
                        OMCard {
                            OMG5StateView(
                                state: .empty,
                                message: "打开上面的分类，这里会列出成局、日程和消息提醒。"
                            )
                        }
                    } else {
                        OMCard(tight: true) {
                            ForEach(Array(model.visibleInbox.enumerated()), id: \.element.id) { index, item in
                                OMRow(
                                    icon: icon(for: item.resolvedCategory),
                                    title: item.summary,
                                    sub: "\(item.categoryLabel) · \(Self.relativeLabel(item.createdAt))",
                                    showsDivider: index < model.visibleInbox.count - 1,
                                    onTap: { open(item) }
                                )
                                .accessibilityIdentifier("notification-row-\(item.id)")
                            }
                        }
                        .accessibilityIdentifier("notification-inbox")
                    }
                    if let error = model.error {
                        OMCard { OMG5StateView(state: .networkError, message: error) }
                    }
                    OMButton(model.saving ? "保存中…" : "保存偏好", icon: .bell, loading: model.saving) {
                        Task {
                            if let saved = await model.save() {
                                await environment.applyCalendarPreference(
                                    enabled: saved.calendarSyncEnabled
                                )
                            }
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s4)
                } else {
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task {
            await model.load()
            if let value = model.value {
                await environment.cacheCalendarPreference(value.calendarSyncEnabled)
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M7-notification-settings")
    }
    private func binding(_ path: WritableKeyPath<NotificationPreferences, Bool>) -> Binding<Bool> {
        Binding(
            get: { model.value?[keyPath: path] ?? false },
            set: { newValue in
                guard var current = model.value else { return }
                current[keyPath: path] = newValue
                model.value = current
            }
        )
    }
    private func category(_ path: WritableKeyPath<NotificationPreferences.Categories, Bool>) -> Binding<Bool> {
        Binding(
            get: { model.value?.categories[keyPath: path] ?? false },
            set: { newValue in
                guard var current = model.value else { return }
                current.categories[keyPath: path] = newValue
                model.value = current
            }
        )
    }
    private func icon(for category: String) -> OMIcon {
        switch category {
        case "schedule_reminders": .cal
        case "chat_messages": .chat
        case "action_updates": .doc
        case "trust_updates": .shield
        case "competition_deadlines": .trophy
        default: .flag
        }
    }
    private func open(_ item: InboxNotification) {
        if let url = NotificationDeepLinkParser.url(from: item.routingUserInfo) {
            router.handle(url: url, isAuthenticated: true)
        }
    }
    private static func relativeLabel(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.unitsStyle = .short
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}

/// DEBUG · 联调诊断
struct DiagnosticsView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var requestID: String?
    @State private var path: String?
    @State private var referenceVersion: String?
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "内部工具", title: "联调诊断")
                OMCard {
                    HStack(spacing: 8) {
                        Image(systemName: environment.networkMonitor.isOnline ? "wifi" : "wifi.slash")
                        Text(environment.networkMonitor.isOnline ? "网络可用" : "离线")
                    }
                    .font(OMTheme.TypeToken.callout.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    Text("API · \(Bundle.main.object(forInfoDictionaryKey: "APIBaseURL") as? String ?? "missing")")
                        .font(OMTheme.TypeToken.mono(.caption))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .padding(.top, OMTheme.Spacing.s2)
                    Text("Reference · \(referenceVersion ?? "checking")")
                        .font(OMTheme.TypeToken.mono(.caption))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .padding(.top, 4)
                    OMDebugRequestID(requestID: requestID)
                    if let path {
                        Text(path)
                            .font(OMTheme.TypeToken.mono(.caption))
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .padding(.top, 4)
                    }
                }
                OMButton("刷新诊断") { Task { await refresh() } }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await refresh() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-debug-diagnostics")
    }
    private func refresh() async { let snapshot = await environment.diagnostics.snapshot(); requestID = snapshot.0; path = snapshot.1; referenceVersion = await environment.referenceData.bundleVersion }
}
