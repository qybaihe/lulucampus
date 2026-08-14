import SwiftUI

@MainActor
private final class DisplayNameEditorModel: ObservableObject {
    @Published var name: String
    @Published var working = false
    @Published var error: String?

    private let repository: IdentityRepository

    init(repository: IdentityRepository, currentName: String) {
        self.repository = repository
        name = currentName
    }

    var trimmed: String {
        name.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var canSave: Bool {
        let value = trimmed
        return (1...20).contains(value.count) && !working
    }

    func save() async -> IdentityFacts? {
        guard canSave else { return nil }
        working = true
        error = nil
        defer { working = false }
        do {
            return try await repository.updateDisplayName(trimmed)
        } catch {
            self.error = error.localizedDescription
            return nil
        }
    }
}

/// 「我」页修改对外展示的昵称。学院/专业等校方事实仍不可改。
struct DisplayNameEditorView: View {
    @StateObject private var model: DisplayNameEditorModel
    @Environment(\.dismiss) private var dismiss
    var onSaved: (IdentityFacts) -> Void

    init(
        repository: IdentityRepository,
        currentName: String,
        onSaved: @escaping (IdentityFacts) -> Void
    ) {
        _model = StateObject(
            wrappedValue: DisplayNameEditorModel(repository: repository, currentName: currentName)
        )
        self.onSaved = onSaved
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(title: "修改昵称", lulu: .homeReply)
                    OMCard {
                        Text("这个名字会出现在消息、局和搭子里")
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                        TextField("1–20 个字", text: $model.name)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .modifier(OMInputStyle())
                            .padding(.top, OMTheme.Spacing.s3)
                            .onChange(of: model.name) { _, value in
                                if value.count > 20 {
                                    model.name = String(value.prefix(20))
                                }
                            }
                            .accessibilityIdentifier("display-name-field")
                        HStack {
                            Spacer()
                            Text("\(model.trimmed.count)/20")
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                        .padding(.top, 6)
                    }
                    if let error = model.error {
                        OMCard {
                            OMG5StateView(state: .networkError, message: error)
                        }
                    }
                    OMButton("保存昵称", systemIcon: "checkmark.circle.fill", loading: model.working, disabledReason: model.canSave ? nil : "请填写 1–20 个字") {
                        Task {
                            if let updated = await model.save() {
                                onSaved(updated)
                                dismiss()
                            }
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("关闭") { dismiss() }
                }
            }
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("screen-display-name-editor")
        }
    }
}
