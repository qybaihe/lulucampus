import SwiftUI

/// A1 · 首次进入引导（品牌页 → 选学校，Lulu 全程陪伴）
struct OnboardingView: View {
    let stateID: String
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @State private var step: Int = {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if let i = args.firstIndex(of: "-OnboardingStep"), args.indices.contains(i + 1),
           let value = Int(args[i + 1]) { return value }
        #endif
        return 0
    }()
    @State private var school: SchoolAffiliation? = SchoolAffiliation.current

    private let brandPages: [(clip: LuluClip, title: String, subtitle: String)] = [
        (.homeIdle,
         AppBrand.displayName,
         "\(AppBrand.slogan)。从真实课业与校园场景出发——拼课、约球、组队比赛，不刷人、不闲聊。"),
        (.homeListening,
         "说一句，剩下的交给噜噜",
         "想找什么人、什么时候有空，告诉 \(AppBrand.agentName) 一句话，噜噜帮你把缺口补齐。"),
    ]
    /// 0…brandPages-1 品牌页；最后一页选学校。
    private var pageCount: Int { brandPages.count + 1 }
    private var isSchoolStep: Bool { step >= brandPages.count }

    var body: some View {
        VStack(spacing: 0) {
            TabView(selection: $step) {
                ForEach(Array(brandPages.enumerated()), id: \.offset) { index, page in
                    VStack(spacing: 0) {
                        Text(page.title)
                            .font(OMTheme.TypeToken.title2)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .multilineTextAlignment(.center)
                            .padding(.top, 8)
                            .padding(.horizontal, 24)
                        Text(page.subtitle)
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .multilineTextAlignment(.center)
                            .padding(.horizontal, 28)
                            .padding(.top, 6)
                        Spacer(minLength: 8)
                        LuluView(clip: page.clip, placement: .hero)
                            .frame(maxWidth: .infinity)
                            .frame(height: 260)
                        Spacer(minLength: 8)
                    }
                    .tag(index)
                }
                schoolPage.tag(brandPages.count)
            }
            .tabViewStyle(.page(indexDisplayMode: .never))
            .animation(.spring(response: 0.42, dampingFraction: 0.86), value: step)

            HStack(spacing: 8) {
                ForEach(0..<pageCount, id: \.self) { index in
                    Capsule()
                        .fill(index == step ? OMTheme.ColorToken.gap : OMTheme.ColorToken.line)
                        .frame(width: index == step ? 22 : 8, height: 8)
                }
            }
            .animation(.spring(response: 0.3, dampingFraction: 0.8), value: step)
            .padding(.bottom, 18)

            OMButton(
                isSchoolStep ? "开始使用" : "继续",
                icon: .arrow,
                disabledReason: isSchoolStep && school == nil ? "请先选择学校" : nil
            ) {
                if !isSchoolStep {
                    withAnimation(.spring(response: 0.42, dampingFraction: 0.86)) { step += 1 }
                } else if let school {
                    SchoolAffiliation.save(school)
                    if school != .sysu { SchoolAffiliation.campusGatePassed = false }
                    router.popToRoot()
                    router.resumePending()
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 34)
            .accessibilityIdentifier(isSchoolStep ? "onboarding-school-continue" : "onboarding-continue")
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-\(stateID)-onboarding")
    }

    /// 选学校：标题 → 中间噜噜 → 底部两个选项。
    private var schoolPage: some View {
        VStack(spacing: 0) {
            Text("你在哪所学校？")
                .font(OMTheme.TypeToken.title2)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.top, 8)
            Text("我们为部分学校做了针对优化，选项效力相同。")
                .font(OMTheme.TypeToken.footnote)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 28)
                .padding(.top, 6)
            Spacer(minLength: 8)
            LuluView(clip: .coreCare, placement: .hero)
                .frame(maxWidth: .infinity)
                .frame(height: 220)
            Spacer(minLength: 8)
            VStack(spacing: 10) {
                ForEach(SchoolAffiliation.allCases) { option in
                    schoolOption(option)
                }
            }
            .padding(.horizontal, 24)
            .padding(.bottom, 8)
        }
    }

    private func schoolOption(_ option: SchoolAffiliation) -> some View {
        let selected = school == option
        return Button {
            withAnimation(OMTheme.Motion.fast) { school = option }
        } label: {
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 4) {
                    Text(option.title)
                        .font(OMTheme.TypeToken.callout.weight(.bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    Text(option.subtitle)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .multilineTextAlignment(.leading)
                }
                Spacer(minLength: 0)
                Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 22, weight: .semibold))
                    .foregroundStyle(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
            }
            .padding(16)
            .background(OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.large))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                    .stroke(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: selected ? 1.5 : OMTheme.Radius.borderWidth)
            }
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("onboarding-school-\(option.rawValue)")
    }
}

/// A2 · 认证流：先手机号登录/注册；中大账号登录后再绑定校园身份。
struct AuthenticationFlowView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var school: SchoolAffiliation? = SchoolAffiliation.current
    @State private var phase: Phase = .resolve

    private enum Phase: Equatable {
        case school
        case phone
        case resolve
    }

    var body: some View {
        Group {
            switch phase {
            case .resolve:
                Color.clear.onAppear { resolve() }
            case .school:
                schoolGate
            case .phone:
                PhoneAuthView()
            }
        }
        // 勿用 accessibilityElement(children: .contain) 包整页：会按内容固有宽度收缩成中间竖条。
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(OMPageBackground())
        .accessibilityIdentifier("screen-A2-auth-intro")
    }

    private func resolve() {
        phase = school == nil ? .school : .phone
    }

    private var schoolGate: some View {
        OMStage(title: "你在哪所学校？", subtitle: "选好后用手机号登录；中大同学登录后可绑定校园身份", clip: .homeReply) {
            ForEach(SchoolAffiliation.allCases) { option in
                Button {
                    SchoolAffiliation.save(option)
                    school = option
                    withAnimation(OMTheme.Motion.medium) { phase = .phone }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(option.title)
                                .font(OMTheme.TypeToken.callout.weight(.bold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                            Text(option.subtitle)
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        Spacer()
                        Text("›")
                            .font(.system(size: 16, weight: .bold))
                            .foregroundStyle(OMTheme.ColorToken.sage)
                    }
                    .padding(16)
                    .background(OMTheme.ColorToken.card)
                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.large))
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                }
                .buttonStyle(.plain)
                .accessibilityIdentifier("auth-school-\(option.rawValue)")
            }
        }
    }
}

@MainActor
final class FirstUseSetupViewModel: ObservableObject {
    enum Step { case campusBind, grants, facts, social, ready }
    @Published var step: Step = SchoolAffiliation.current == .sysu ? .campusBind : .grants
    @Published var selectedScopes: Set<String> = ["timetable", "curriculum", "enrollment", "agent_booking"]
    @Published var facts: IdentityFacts?
    @Published var working = false
    @Published var error: String?
    private let repository: IdentityRepository
    init(repository: IdentityRepository) { self.repository = repository }

    /// 中大且尚未校园核验 → 先绑定；否则直接授权。
    func bootstrap() async {
        do {
            let facts = try await repository.facts()
            self.facts = facts
            error = nil
            if SchoolAffiliation.current == .sysu && !facts.verified && !SchoolAffiliation.campusGatePassed {
                step = .campusBind
            } else {
                step = .grants
            }
        } catch {
            self.error = error.localizedDescription
            step = SchoolAffiliation.current == .sysu && !SchoolAffiliation.campusGatePassed ? .campusBind : .grants
        }
    }

    func markCampusBound() {
        SchoolAffiliation.campusGatePassed = true
        step = .grants
    }

    func saveGrants() async {
        guard !working else { return }; working = true; defer { working = false }
        do {
            for scope in ["timetable", "curriculum", "enrollment", "agent_booking"] {
                _ = try await repository.setGrant(scope: scope, granted: selectedScopes.contains(scope))
            }
            facts = try await repository.facts(); error = nil; step = .facts
        } catch { self.error = error.localizedDescription }
    }
    func refreshFacts() async {
        do { facts = try await repository.facts(); error = nil } catch { self.error = error.localizedDescription }
    }
    func enableSocial() async {
        guard !working else { return }; working = true; defer { working = false }
        do { _ = try await repository.enableSocial(); error = nil; step = .ready }
        catch { self.error = error.localizedDescription }
    }
    func keepSocialOff() async {
        guard !working else { return }; working = true; defer { working = false }
        do {
            _ = try await repository.setSocialEnabled(false)
            error = nil
            step = .ready
        } catch { self.error = error.localizedDescription }
    }
}

/// A4–A7 · 首次设置（中大可先绑定校园 → 授权 → 身份事实 → 社交 → 就绪）
struct FirstUseSetupView: View {
    @StateObject private var model: FirstUseSetupViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    init(repository: IdentityRepository) { _model = StateObject(wrappedValue: FirstUseSetupViewModel(repository: repository)) }

    private static let grantItems: [(title: String, scope: String)] = [
        ("课表与空闲", "timetable"),
        ("课程画像", "curriculum"),
        ("同课匹配", "enrollment"),
        ("校园预约代理", "agent_booking"),
    ]

    var body: some View {
        Group {
            switch model.step {
            case .campusBind:
                RealLoginView(
                    bindMode: true,
                    onCampusGateComplete: { model.markCampusBound() },
                    onSkip: { model.step = .grants }
                )
            case .grants:
                grants
            case .social:
                social
            case .facts:
                facts
            case .ready:
                ready
            }
        }
        .background(OMPageBackground())
        .task { await model.bootstrap() }
    }

    /// 授权页：标题 → 中间噜噜 → 底部四格选项。
    private var grants: some View {
        OMStage(title: "授权由你掌控", subtitle: "点选你愿意开放的数据边界，随时可在设置里撤回", clip: .coreCare) {
            LazyVGrid(columns: [GridItem(.flexible(), spacing: 10), GridItem(.flexible(), spacing: 10)], spacing: 10) {
                ForEach(Self.grantItems, id: \.scope) { item in
                    grantButton(title: item.title, scope: item.scope)
                }
            }
            if let error = model.error {
                Text(error)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(Color.red.opacity(0.85))
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            OMButton("确认授权，继续", loading: model.working) {
                Task { await model.saveGrants() }
            }
            .accessibilityIdentifier("first-use-save-grants")
        }
        .accessibilityIdentifier("screen-A4-grants")
    }

    private func grantButton(title: String, scope: String) -> some View {
        let on = model.selectedScopes.contains(scope)
        return Button {
            withAnimation(OMTheme.Motion.fast) {
                if on { model.selectedScopes.remove(scope) }
                else { model.selectedScopes.insert(scope) }
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: on ? "checkmark.circle.fill" : "circle")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(on ? OMTheme.ColorToken.ink : OMTheme.ColorToken.sage)
                Text(title)
                    .font(OMTheme.TypeToken.footnote.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 12)
            .frame(maxWidth: .infinity, minHeight: 52, alignment: .leading)
            .background(on ? OMTheme.ColorToken.yolk.opacity(0.35) : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.medium))
            .overlay {
                RoundedRectangle(cornerRadius: OMTheme.Radius.medium)
                    .stroke(on ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: on ? 1.5 : OMTheme.Radius.borderWidth)
            }
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("first-use-grant-\(scope)")
    }
    private var facts: some View {
        OMStage(title: "确认你的校园画像", subtitle: "来自校园身份核验，只给你自己看", clip: .homeReply) {
            if let facts = model.facts {
                OMCard {
                    OMTextRole.t3(facts.verified ? "校园身份已核验" : "身份待核验")
                    let line = [facts.college, facts.major].compactMap { $0 }.joined(separator: " · ")
                    if !line.isEmpty {
                        OMTextRole.call(line).padding(.top, 4)
                    }
                    let meta = [facts.campus, facts.gradeYear.map(String.init)].compactMap { $0 }.joined(separator: " · ")
                    if !meta.isEmpty {
                        OMTextRole.foot(meta).padding(.top, 2)
                    }
                }
            } else if let error = model.error {
                Text(error)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(Color.red.opacity(0.85))
            } else {
                OMTextRole.foot(AppBrand.loadingMessage)
            }
            OMButton("身份事实无误", icon: .shield) { model.step = .social }
                .accessibilityIdentifier("first-use-confirm-facts")
        }
        .task { if model.facts == nil { await model.refreshFacts() } }
        .accessibilityIdentifier("screen-A5-A6-facts")
    }

    /// 社交开关：标题 → 中间噜噜 → 底部双按钮。
    private var social: some View {
        OMStage(title: "由你开启校园成局", subtitle: "开启后才能发布意图与加入局", clip: .confirmGather) {
            if let error = model.error {
                Text(error)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(Color.red.opacity(0.85))
            }
            OMButton("开启并继续", loading: model.working) {
                Task { await model.enableSocial() }
            }
            .accessibilityIdentifier("first-use-enable-social")
            OMButton(model.working ? "保存中…" : "暂不开启，保持关闭并继续", kind: .ghost) {
                Task { await model.keepSocialOff() }
            }
            .disabled(model.working)
            .accessibilityIdentifier("first-use-skip-social")
        }
        .accessibilityIdentifier("screen-A7-social")
    }

    private var ready: some View {
        OMStage(title: "准备好了", subtitle: "首次设置已保存，噜噜在今天等你", clip: .coreCelebrate) {
            OMButton("进入今天", icon: .arrow) {
                Task {
                    await environment.session.completeOnboarding()
                    router.selectedTab = .today
                    router.popToRoot()
                    router.resumePending()
                    let scope = await environment.auth.cacheScope()
                    environment.recovery.restoreNavigation(scope: scope, into: router)
                }
            }
            .accessibilityIdentifier("first-use-finish")
        }
        .accessibilityIdentifier("screen-A7-ready")
    }
    private func retry() async {
        switch model.step {
        case .campusBind: await model.bootstrap()
        case .grants: await model.saveGrants()
        case .facts: await model.refreshFacts()
        case .social: await model.enableSocial()
        case .ready: break
        }
    }
}
