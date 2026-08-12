#if DEBUG
import SwiftUI

enum PrototypeAction: Hashable {
    case back
    case named(String)
    case openExternalRegistration
    case openSystemSettings
    case share
    case sendMessage
}

struct PrototypeActions {
    var route: (PrototypeScreenID) -> Void
    var perform: (PrototypeAction) -> Void

    static let preview = PrototypeActions(route: { _ in }, perform: { _ in })
}

/// 视觉状态库：74 正式节点 + MSG + B12.2，逐屏比对 mobile-ios.html。
struct PrototypeGalleryView: View {
    @State private var path: [PrototypeScreenID]
    private let externalActions: PrototypeActions?

    init(initialScreen: PrototypeScreenID? = nil, actions: PrototypeActions? = nil) {
        _path = State(initialValue: initialScreen.map { [$0] } ?? [])
        externalActions = actions
    }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 0) {
                    galleryHeader
                    ForEach(PrototypeScreenGroup.allCases) { group in
                        let screens = PrototypeScreenID.allCases.filter { $0.group == group }
                        if !screens.isEmpty {
                            OMSection(title: "\(group.rawValue) · \(screens.count)")
                            OMCard(tight: true) {
                                ForEach(screens) { screen in
                                    galleryRow(screen)
                                }
                            }
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationTitle("视觉状态库")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(for: PrototypeScreenID.self) { screen in
                PrototypeScreenView(screen: screen, actions: actions(for: screen))
                    .toolbar(.hidden, for: .navigationBar)
            }
        }
        .preferredColorScheme(.light)
    }

    private var galleryHeader: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("\(AppBrand.displayName) · 噜噜亮色稿")
                .font(OMTheme.TypeToken.footnote.weight(.bold))
                .tracking(2)
                .foregroundStyle(OMTheme.ColorToken.mist)
            Text("76 个可达视觉状态")
                .font(OMTheme.TypeToken.hero)
                .tracking(-0.7)
            Text("74 个正式节点 + MSG + B12.2 · 视觉事实源 2026-08-12 噜噜亮色稿")
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, 12)
    }

    private func galleryRow(_ screen: PrototypeScreenID) -> some View {
        Button {
            path.append(screen)
        } label: {
            HStack(spacing: 12) {
                Text(screen.rawValue)
                    .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .frame(width: 48, alignment: .leading)
                VStack(alignment: .leading, spacing: 3) {
                    Text(screen.title)
                        .font(OMTheme.TypeToken.callout.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    Text(screen.route)
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                Spacer()
                if !screen.isFormalNode {
                    OMChip(text: "组合态", kind: .soft)
                }
                Text("›")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.sage)
            }
            .padding(.vertical, 13)
            .frame(minHeight: 48)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .overlay(alignment: .bottom) {
            Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
        }
        .accessibilityIdentifier("prototype-row-\(screen.rawValue)")
    }

    private func actions(for screen: PrototypeScreenID) -> PrototypeActions {
        if let externalActions { return externalActions }
        return PrototypeActions(
            route: { target in path.append(target) },
            perform: { action in
                if action == .back, !path.isEmpty { path.removeLast() }
            }
        )
    }
}
#endif
