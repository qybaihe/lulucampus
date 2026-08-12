import SwiftUI

struct AccountExportFileWriter: Sendable {
    let root: URL

    init(root: URL? = nil) {
        self.root = root ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appending(path: "OneMore/Exports", directoryHint: .isDirectory)
    }

    func write(_ value: [String: JSONValue], now: Date = .now) throws -> URL {
        try FileManager.default.createDirectory(
            at: root,
            withIntermediateDirectories: true,
            attributes: [.protectionKey: FileProtectionType.complete]
        )
        var directory = URLResourceValues()
        directory.isExcludedFromBackup = true
        var protectedRoot = root
        try protectedRoot.setResourceValues(directory)
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.dateFormat = "yyyyMMdd-HHmmss"
        let url = root.appending(path: "one-more-data-\(formatter.string(from: now)).json")
        let encoder = JSONEncoder.oneMore
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        try encoder.encode(value).write(to: url, options: [.atomic, .completeFileProtection])
        return url
    }
}

/// M10 · 数据与账号
struct AccountDataView: View {
    let repository: IdentityRepository
    @EnvironmentObject private var environment: AppEnvironment
    @State private var exporting = false
    @State private var exportSummary: String?
    @State private var exportURL: URL?
    @State private var error: String?
    @State private var confirmsDeletion = false
    @State private var deleting = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "账号与数据", title: "数据与账号", lulu: .homeIdle)
                if let exportSummary {
                    OMCard {
                        OMTextRole.foot(exportSummary)
                    }
                }
                OMButton("生成我的数据导出", systemIcon: "square.and.arrow.down", loading: exporting) {
                    Task { await export() }
                }
                .accessibilityIdentifier("account-export")
                if let exportURL {
                    ShareLink(item: exportURL, preview: SharePreview("\(AppBrand.displayName) · 我的数据", image: Image(systemName: "doc.text"))) {
                        Label("保存或分享 JSON 文件", systemImage: "square.and.arrow.up")
                            .font(OMTheme.TypeToken.body.weight(.bold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(maxWidth: .infinity, minHeight: 52)
                            .background(OMTheme.ColorToken.yolk)
                            .clipShape(Capsule())
                            .overlay { Capsule().stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth) }
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    .accessibilityIdentifier("account-export-share")
                }
                OMCard {
                    HStack(spacing: 10) {
                        Image(om: .warn)
                            .font(.system(size: 17))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(width: 38, height: 38)
                            .background(OMTheme.ColorToken.gapSoft)
                            .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                        OMTextRole.t3("注销账号")
                        Spacer()
                    }
                    OMButton("注销账号…", kind: .dark, small: true, fillsWidth: false, loading: deleting) {
                        confirmsDeletion = true
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                    .accessibilityIdentifier("account-delete")
                }
                if let error {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .alert("确认注销账号？", isPresented: $confirmsDeletion) {
            Button("取消", role: .cancel) {}
            Button("永久注销", role: .destructive) { Task { await deleteAccount() } }
        } message: { Text("上传媒体和校园授权将被清理，此操作不可撤回。") }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-M10-account")
    }
    private func export() async {
        guard !exporting else { return }; exporting = true; defer { exporting = false }
        do {
            let value = try await repository.exportData()
            if let previous = exportURL { try? FileManager.default.removeItem(at: previous) }
            exportURL = try AccountExportFileWriter().write(value)
            exportSummary = "导出已生成，共 \(value.keys.count) 个数据分区，可保存或分享。"
            error = nil
        } catch { self.error = error.localizedDescription }
    }
    private func deleteAccount() async {
        guard !deleting else { return }; deleting = true; defer { deleting = false }
        do { _ = try await repository.deleteAccount(); try await environment.session.signOut() }
        catch { self.error = error.localizedDescription }
    }
}
