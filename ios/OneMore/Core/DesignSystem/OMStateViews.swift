import SwiftUI

// MARK: - 骨架屏

struct OMSkeleton: View {
    var rows = 3

    var body: some View {
        VStack(spacing: 12) {
            ForEach(0..<rows, id: \.self) { index in
                RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                    .fill(OMTheme.ColorToken.card)
                    .frame(height: index == 0 ? 96 : 74)
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .overlay(alignment: .leading) {
                        VStack(alignment: .leading, spacing: 9) {
                            RoundedRectangle(cornerRadius: 3)
                                .fill(OMTheme.ColorToken.ink12)
                                .frame(width: index == 0 ? 170 : 120, height: 10)
                            RoundedRectangle(cornerRadius: 3)
                                .fill(OMTheme.ColorToken.ink06)
                                .frame(width: 220, height: 8)
                        }
                        .padding(16)
                    }
                    .accessibilityLabel("正在加载")
            }
        }
    }
}

// MARK: - G5 八个全局状态（一套系统，页面不各写各的）

enum OMG5State: String, CaseIterable {
    case loading
    case empty
    case networkError = "network-error"
    case offline
    case permissionDenied = "permission-denied"
    case sessionExpired = "session-expired"
    case duplicateTap = "duplicate-tap"
    case staleState = "stale-state"

    var clip: LuluClip {
        switch self {
        case .loading, .staleState: .homeThinking
        case .empty: .homeIdle
        case .networkError, .offline, .permissionDenied, .sessionExpired: .coreCare
        case .duplicateTap: .homeReply
        }
    }

    var title: String {
        switch self {
        case .loading: "正在加载"
        case .empty: "这里还空着"
        case .networkError: "网络开了小差"
        case .offline: "当前离线"
        case .permissionDenied: "这个权限还没开"
        case .sessionExpired: "登录状态失效了"
        case .duplicateTap: "已经收到啦"
        case .staleState: "内容可能不是最新"
        }
    }

    var defaultMessage: String {
        switch self {
        case .loading: AppBrand.loadingMessage
        case .empty: "暂时没有内容。有进展时，噜噜会来告诉你。"
        case .networkError: "请求没有发出去。检查网络后再试一次，已填的内容都在。"
        case .offline: "你现在看到的是上次同步的内容。恢复网络后会自动更新。"
        case .permissionDenied: "没有它，这部分功能用不了。你可以随时在设置里改主意。"
        case .sessionExpired: "出于安全考虑需要重新认证。用企业微信扫一下就好，进度不会丢。"
        case .duplicateTap: "这个操作正在处理，不用重复点。"
        case .staleState: "这页数据更新于 12 分钟前。下拉可以刷新。"
        }
    }

    var defaultAction: (title: String, kind: OMButtonKind)? {
        switch self {
        case .networkError: ("重新加载", .primary)
        case .permissionDenied: ("去系统设置开启", .primary)
        case .sessionExpired: ("重新扫码认证", .primary)
        case .staleState: ("刷新", .ghost)
        default: nil
        }
    }
}

/// .state-view：Lulu 空错态插画 + 标题 + 描述 + 可选动作（最大 240 宽居中）
struct OMG5StateView: View {
    let state: OMG5State
    var message: String? = nil
    var actionTitle: String? = nil
    var action: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 0) {
            LuluView(clip: state.clip, placement: .empty)
            Text(state.title)
                .font(OMTheme.TypeToken.title2)
                .padding(.top, OMTheme.Spacing.s4)
            Text(message ?? state.defaultMessage)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .lineSpacing(4)
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s2)
            if let spec = state.defaultAction {
                OMButton(actionTitle ?? spec.title, kind: spec.kind) { action?() }
                    .frame(maxWidth: 240)
                    .padding(.top, OMTheme.Spacing.s5)
            } else if let actionTitle, let action {
                OMButton(actionTitle, action: action)
                    .frame(maxWidth: 240)
                    .padding(.top, OMTheme.Spacing.s5)
            }
        }
        .padding(.horizontal, OMTheme.Spacing.s4)
        .padding(.vertical, OMTheme.Spacing.s8)
        .frame(maxWidth: .infinity)
        .accessibilityElement(children: .contain)
    }
}

#if DEBUG
/// 旧启动参数 `-StateEvidence` 的取值保持兼容，直接映射到 G5。
typealias RuntimeStateEvidence = OMG5State

/// 跨屏恢复状态的确定性原生证据视图，使用生产设计系统组件而非系统弹窗。
struct RuntimeStateEvidenceView: View {
    let state: RuntimeStateEvidence
    @State private var feedback: String?

    var body: some View {
        ZStack {
            OMPageBackground()
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("STATE EVIDENCE · \(state.rawValue.uppercased())")
                        .font(OMTheme.TypeToken.footnote.weight(.bold))
                        .tracking(2)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                    content
                    if let feedback {
                        Text(feedback)
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .accessibilityIdentifier("state-evidence-feedback")
                    }
                    Text("同一恢复组件用于真实网络、权限与会话状态。")
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.top, 24)
                .padding(.bottom, 44)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .preferredColorScheme(.light)
        .accessibilityIdentifier("runtime-state-library")
        .accessibilityIdentifier("state-evidence-\(state.rawValue)")
    }

    @ViewBuilder private var content: some View {
        switch state {
        case .loading:
            OMSkeleton(rows: 3)
            HStack(spacing: 10) {
                ProgressView().tint(OMTheme.ColorToken.ink)
                Text(AppBrand.loadingMessage)
            }
            .font(OMTheme.TypeToken.callout).foregroundStyle(OMTheme.ColorToken.mist)
        default:
            OMG5StateView(state: state) { feedback = "已触发：\(state.title)" }
        }
    }
}
#endif
