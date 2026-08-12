import SwiftUI

@MainActor
private final class ProfileEditorViewModel: ObservableObject {
    enum Phase {
        case loading
        case loaded(UserProfilePayload)
        case failed(String)
    }

    @Published var phase: Phase = .loading
    @Published var selectedSelfReported: Set<String> = []
    @Published var hiddenVerified: Set<String> = []
    @Published var working = false
    @Published var resultMessage: String?

    private let repository: IdentityRepository

    init(repository: IdentityRepository) {
        self.repository = repository
    }

    func load() async {
        phase = .loading
        resultMessage = nil
        do {
            apply(try await repository.profile())
        } catch {
            phase = .failed(error.localizedDescription)
        }
    }

    func save() async {
        guard !working else { return }
        working = true
        resultMessage = nil
        defer { working = false }
        do {
            let profile = try await repository.updateProfileTags(
                selfReported: selectedSelfReported.sorted(),
                hiddenVerified: hiddenVerified.sorted()
            )
            apply(profile)
            resultMessage = "画像设置已保存；能力标签与兴趣画像会用于匹配，成局后成员可见兴趣 chips。"
        } catch {
            resultMessage = error.localizedDescription
        }
    }

    func toggleSelfReported(_ key: String) {
        if selectedSelfReported.contains(key) {
            selectedSelfReported.remove(key)
        } else {
            selectedSelfReported.insert(key)
        }
    }

    func toggleVerifiedVisibility(_ key: String) {
        if hiddenVerified.contains(key) {
            hiddenVerified.remove(key)
        } else {
            hiddenVerified.insert(key)
        }
    }

    private func apply(_ profile: UserProfilePayload) {
        selectedSelfReported = Set(
            profile.capabilities
                .filter { $0.source == "self_reported" }
                .map(\.key)
        )
        hiddenVerified = Set(
            profile.capabilities
                .filter { $0.source == "verified" && $0.hidden }
                .map(\.key)
        )
        phase = .loaded(profile)
    }
}

/// M2 · 画像与能力
struct ProfileEditorView: View {
    @StateObject private var model: ProfileEditorViewModel

    init(repository: IdentityRepository) {
        _model = StateObject(
            wrappedValue: ProfileEditorViewModel(repository: repository)
        )
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(title: "画像与能力", lulu: .homeReply)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(profile):
                    identityCard(profile)
                    verifiedCard(profile)
                    selfReportedCard(profile)
                    OMButton("保存画像设置", systemIcon: "checkmark.circle.fill", loading: model.working) {
                        Task { await model.save() }
                    }
                }
                if let message = model.resultMessage {
                    OMCard {
                        OMTextRole.foot(message)
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M2-profile-editor")
    }

    private func identityCard(_ profile: UserProfilePayload) -> some View {
        OMCard {
            HStack(spacing: 10) {
                OMSticker("id-card.png", size: .s44)
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("校方认证事实")
                }
                Spacer()
            }
            OMDivider()
            identityRow("学院", profile.identity.string("college"))
            identityRow("专业", profile.identity.string("major"))
            identityRow("年级", profile.identity.string("grade_year"))
            identityRow("校区", profile.identity.string("campus"))
        }
    }

    private func verifiedCard(_ profile: UserProfilePayload) -> some View {
        let items = profile.capabilities.filter { $0.source == "verified" }
        return OMCard {
            OMTextRole.t3("认证能力")
            if items.isEmpty {
                OMTextRole.foot("暂无认证能力标签").padding(.top, OMTheme.Spacing.s2)
            }
            ForEach(items) { item in
                HStack {
                    Text(item.label).font(OMTheme.TypeToken.callout.weight(.semibold))
                    Spacer()
                    OMSwitch(isOn: Binding(
                        get: { !model.hiddenVerified.contains(item.key) },
                        set: { _ in model.toggleVerifiedVisibility(item.key) }
                    ))
                }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("verified-capability-\(item.key)")
            }
        }
    }

    private func selfReportedCard(_ profile: UserProfilePayload) -> some View {
        let verifiedKeys = Set(
            profile.capabilities.filter { $0.source == "verified" }.map(\.key)
        )
        let options = profile.availableCapabilities.filter {
            !verifiedKeys.contains($0.key)
        }
        return OMCard {
            OMTextRole.t3("自述能力")
            if options.isEmpty {
                OMTextRole.foot("暂无可选能力标签").padding(.top, OMTheme.Spacing.s2)
            }
            OMFlowLayout {
                ForEach(options) { option in
                    let selected = model.selectedSelfReported.contains(option.key)
                    Button {
                        model.toggleSelfReported(option.key)
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: selected ? "checkmark.circle.fill" : "circle")
                            Text(option.label)
                        }
                        .font(OMTheme.TypeToken.caption.weight(.bold))
                        .foregroundStyle(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 4)
                        .background(selected ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.card)
                        .clipShape(Capsule())
                        .overlay {
                            Capsule().stroke(selected ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                        .fixedSize()
                    }
                    .buttonStyle(.plain)
                    .disabled(
                        !selected && model.selectedSelfReported.count >= 30
                    )
                    .accessibilityIdentifier("self-capability-\(option.key)")
                }
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
    }

    private func identityRow(_ label: String, _ value: String?) -> some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label).foregroundStyle(OMTheme.ColorToken.mist)
            Spacer()
            Text(value?.isEmpty == false ? value! : "未提供")
                .foregroundStyle(OMTheme.ColorToken.ink)
                .multilineTextAlignment(.trailing)
        }
        .font(OMTheme.TypeToken.callout)
        .padding(.top, OMTheme.Spacing.s2)
    }
}

private extension Dictionary where Key == String, Value == JSONValue {
    func string(_ key: String) -> String? {
        guard case let .string(value)? = self[key] else { return nil }
        return value
    }
}
