#if DEBUG
import SwiftUI
import UIKit

struct PrototypeHostView: View {
    let initialID: String?
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @Environment(\.openURL) private var openURL
    @State private var feedback: String?
    var body: some View {
        Group {
            if let initialID, let screen = PrototypeScreenID(rawValue: initialID.uppercased()) {
                PrototypeScreenView(
                    screen: screen,
                    actions: PrototypeActions(
                        route: { router.push(.prototypeScreen($0.rawValue)) },
                        perform: handle
                    )
                )
            } else {
                PrototypeGalleryView(
                    actions: PrototypeActions(
                        route: { router.push(.prototypeScreen($0.rawValue)) },
                        perform: handle
                    )
                )
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .overlay(alignment: .top) {
            if let feedback {
                Text(feedback)
                    .font(.caption.bold())
                    .padding(.horizontal, 14)
                    .padding(.vertical, 9)
                    .background(.ultraThinMaterial, in: Capsule())
                    .padding(.top, 8)
                    .transition(.move(edge: .top).combined(with: .opacity))
            }
        }
    }

    private func handle(_ action: PrototypeAction) {
        switch action {
        case .back:
            if !router.path.isEmpty { router.path.removeLast() }
        case .openExternalRegistration:
            openURL(URL(string: "https://math.sysu.edu.cn/article/3910")!)
        case .openSystemSettings:
            environment.permissions.openSystemSettings()
        case .share:
            presentShare(items: ["\(AppBrand.displayName) · 匿名缺口卡", URL(string: "onemore://public-gatherings")!])
        case .sendMessage:
            router.popToRoot(); router.selectedTab = .messages
        case let .named(name):
            withAnimation { feedback = "已触发：\(name)" }
            Task { try? await Task.sleep(for: .seconds(2)); await MainActor.run { withAnimation { feedback = nil } } }
        }
    }

    private func presentShare(items: [Any]) {
        let controller = UIActivityViewController(activityItems: items, applicationActivities: nil)
        guard let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first,
              let root = scene.keyWindow?.rootViewController else { return }
        var presenter = root
        while let presented = presenter.presentedViewController { presenter = presented }
        presenter.present(controller, animated: true)
    }
}
#endif
