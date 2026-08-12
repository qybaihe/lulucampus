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
         "想找什么人、什么时候有空，告诉 Hermes 一句话，噜噜帮你把缺口补齐。"),
    ]
    /// 0…brandPages-1 品牌页；最后一页选学校。
    private var pageCount: Int { brandPages.count + 1 }
    private var isSchoolStep: Bool { step >= brandPages.count }

    var body: some View {
        VStack(spacing: 0) {
            TabView(selection: $step) {
                ForEach(Array(brandPages.enumerated()), id: \.offset) { index, page in
                    VStack(spacing: 18) {
                        Spacer()
                        LuluView(clip: page.clip, placement: .hero)
                            .frame(height: 250)
                        Text(page.title)
                            .font(OMTheme.TypeToken.hero)
                            .tracking(-0.7)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .multilineTextAlignment(.center)
                        Text(page.subtitle)
                            .font(OMTheme.TypeToken.callout)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .padding(.horizontal, 34)
                        Spacer()
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

    /// 选学校：两个选项视觉对等，噜噜陪伴。
    private var schoolPage: some View {
        VStack(spacing: 18) {
            Spacer()
            LuluView(clip: .coreCare, placement: .hero)
                .frame(height: 220)
            Text("你在哪所学校？")
                .font(OMTheme.TypeToken.hero)
                .tracking(-0.7)
                .foregroundStyle(OMTheme.ColorToken.ink)
            Text("我们为部分学校做了针对优化，选项效力相同。")
                .font(OMTheme.TypeToken.callout)
                .multilineTextAlignment(.center)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.horizontal, 34)
            VStack(spacing: 10) {
                ForEach(SchoolAffiliation.allCases) { option in
                    schoolOption(option)
                }
            }
            .padding(.horizontal, 24)
            .padding(.top, 8)
            Spacer()
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

/// A2 · 认证流：中大先扫码闸门 → 全员手机号密码登录。
struct AuthenticationFlowView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var school: SchoolAffiliation? = SchoolAffiliation.current
    @State private var phase: Phase = .resolve

    private enum Phase: Equatable {
        case school
        case campusScan
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
            case .campusScan:
                RealLoginView(campusGateOnly: true) {
                    SchoolAffiliation.campusGatePassed = true
                    withAnimation(OMTheme.Motion.medium) { phase = .phone }
                }
            case .phone:
                PhoneAuthView()
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-A2-auth-intro")
    }

    private func resolve() {
        guard let school else {
            phase = .school
            return
        }
        if school == .sysu && !SchoolAffiliation.campusGatePassed {
            phase = .campusScan
        } else {
            phase = .phone
        }
    }

    private var schoolGate: some View {
        VStack(spacing: 18) {
            Spacer()
            LuluView(clip: .homeReply, placement: .hero).frame(height: 220)
            Text("你在哪所学校？")
                .font(OMTheme.TypeToken.hero)
                .tracking(-0.7)
                .foregroundStyle(OMTheme.ColorToken.ink)
            Text("选好后进入登录；中大同学需先完成校园扫码。")
                .font(OMTheme.TypeToken.callout)
                .multilineTextAlignment(.center)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.horizontal, 30)
            VStack(spacing: 10) {
                ForEach(SchoolAffiliation.allCases) { option in
                    Button {
                        SchoolAffiliation.save(option)
                        school = option
                        withAnimation(OMTheme.Motion.medium) {
                            phase = option == .sysu ? .campusScan : .phone
                        }
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
            .padding(.horizontal, 24)
            Spacer()
        }
        .background(OMPageBackground())
    }
}

@MainActor
final class FirstUseSetupViewModel: ObservableObject {
    enum Step { case grants, facts, social, ready }
    @Published var step: Step = .grants
    @Published var selectedScopes: Set<String> = ["timetable", "curriculum", "enrollment", "agent_booking"]
    @Published var facts: IdentityFacts?
    @Published var working = false
    @Published var error: String?
    private let repository: IdentityRepository
    init(repository: IdentityRepository) { self.repository = repository }
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

/// A4–A7 · 首次设置（授权 → 身份事实 → 社交开启 → 就绪）
struct FirstUseSetupView: View {
    @StateObject private var model: FirstUseSetupViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    init(repository: IdentityRepository) { _model = StateObject(wrappedValue: FirstUseSetupViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                switch model.step {
                case .grants: grants
                case .facts: facts
                case .social: social
                case .ready: ready
                }
                if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await retry() }
                        }
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
    }
    private var grants: some View {
        VStack(alignment: .leading, spacing: 0) {
            OMHeader(eyebrow: "分项授权", title: "授权由你掌控", lulu: .coreCare)
            OMCard {
                grant("课表与空闲", "timetable")
                grant("课程画像", "curriculum")
                grant("同课匹配", "enrollment")
                grant("校园预约代理", "agent_booking")
            }
            OMButton("保存授权并读取身份事实", loading: model.working) {
                Task { await model.saveGrants() }
            }
            .accessibilityIdentifier("first-use-save-grants")
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-A4-grants")
    }
    private func grant(_ title: String, _ scope: String) -> some View {
        HStack {
            Text(title)
                .font(OMTheme.TypeToken.callout.weight(.semibold))
                .foregroundStyle(OMTheme.ColorToken.ink)
            Spacer()
            OMSwitch(isOn: Binding(
                get: { model.selectedScopes.contains(scope) },
                set: { enabled in
                    if enabled {
                        model.selectedScopes.insert(scope)
                    } else {
                        model.selectedScopes.remove(scope)
                    }
                }
            ))
        }
        .padding(.vertical, 6)
    }
    private var facts: some View {
        VStack(alignment: .leading, spacing: 0) {
            OMHeader(eyebrow: "校方核验事实", title: "确认你的校园画像", lulu: .homeReply)
            if let facts = model.facts {
                OMCard {
                    HStack(spacing: 10) {
                        OMSticker("id-card.png", size: .s44)
                        VStack(alignment: .leading, spacing: 2) {
                            OMTextRole.t3(facts.verified ? "统一身份已核验" : "身份待核验")
                        }
                        Spacer()
                    }
                    OMDivider()
                    OMTextRole.t2([facts.college, facts.major].compactMap { $0 }.joined(separator: " · "))
                    OMTextRole.foot([facts.campus, facts.gradeYear.map(String.init)].compactMap { $0 }.joined(separator: " · "))
                        .padding(.top, 4)
                }
            } else {
                OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
            }
            OMButton("身份事实无误", icon: .shield) { model.step = .social }
                .accessibilityIdentifier("first-use-confirm-facts")
        }
        .task { if model.facts == nil { await model.refreshFacts() } }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-A5-A6-facts")
    }
    private var social: some View {
        VStack(alignment: .leading, spacing: 0) {
            OMHeader(eyebrow: "主动开启", title: "由你开启校园成局", lulu: .confirmGather)
            OMCard {
                OMTextRole.call("开启后才能发布意图与加入局。")
            }
            OMButton("开启并继续", loading: model.working) {
                Task { await model.enableSocial() }
            }
            .accessibilityIdentifier("first-use-enable-social")
            OMButton(model.working ? "保存中…" : "暂不开启，保持关闭并继续", kind: .ghost) {
                Task { await model.keepSocialOff() }
            }
            .padding(.top, OMTheme.Spacing.s2)
            .disabled(model.working)
            .accessibilityIdentifier("first-use-skip-social")
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-A7-social")
    }
    private var ready: some View {
        VStack(alignment: .leading, spacing: 0) {
            Spacer(minLength: 40)
            LuluView(clip: .coreCelebrate, placement: .empty)
                .frame(maxWidth: .infinity)
                .padding(.bottom, OMTheme.Spacing.s3)
            Text("准备好了")
                .font(OMTheme.TypeToken.title1).tracking(-0.3)
                .frame(maxWidth: .infinity)
                .multilineTextAlignment(.center)
            OMTextRole.foot("首次设置已保存，噜噜在今天等你。")
                .frame(maxWidth: .infinity)
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s2)
                .padding(.bottom, OMTheme.Spacing.s4)
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
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-A7-ready")
    }
    private func retry() async {
        switch model.step { case .grants: await model.saveGrants(); case .facts: await model.refreshFacts(); case .social: await model.enableSocial(); case .ready: break }
    }
}
