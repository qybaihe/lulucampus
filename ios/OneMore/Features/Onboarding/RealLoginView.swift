import SwiftUI
import UIKit

@MainActor final class RealLoginViewModel: ObservableObject {
    enum Phase { case intro, creating, waiting(LoginSession), failed(String) }
    @Published var phase: Phase = .intro
    private var polling: Task<Void, Never>?
    /// 仅校园闸门：SUCCESS 后不兑换会话，交由上层继续手机号登录。
    var campusGateOnly = false
    var onCampusGateComplete: (() -> Void)?

    func start(api: APIClient, sessionController: AppSessionController, router: AppRouter) async {
        guard polling == nil else { return }; phase = .creating
        do {
            let installID = UserDefaults.standard.string(forKey: "device.install.id") ?? UUID().uuidString
            UserDefaults.standard.set(installID, forKey: "device.install.id")
            let arguments = ProcessInfo.processInfo.arguments
            let resume: String? = {
                guard let index = arguments.firstIndex(of: "-LoginResumeUserID"), arguments.indices.contains(index + 1) else { return nil }
                return arguments[index + 1]
            }()
            let login: LoginSession = try await api.send("/auth/session", method: .post, body: LoginSessionCreate(deviceInstallId: installID, resumeUserId: resume))
            guard let redemptionToken = login.redemptionToken else {
                phase = .failed("服务端未返回本设备的登录兑换凭证")
                return
            }
            phase = .waiting(login)
            #if DEV_AUTH
            if Self.argumentValue("-AutoCompleteLogin", in: arguments)?.uppercased() == "YES" {
                await completeDemo(api: api)
            }
            #endif
            polling = Task { [weak self] in
                guard let self else { return }
                while !Task.isCancelled {
                    do {
                        let current: LoginSession = try await api.get(
                            "/auth/session/\(login.id)",
                            headers: ["X-Login-Redemption": redemptionToken]
                        )
                        self.phase = .waiting(current)
                        if current.status == "SUCCESS" {
                            if self.campusGateOnly {
                                await MainActor.run { self.onCampusGateComplete?() }
                                break
                            }
                            let redeemed: LoginRedemptionResult = try await api.send(
                                "/auth/session/\(login.id)/redeem",
                                method: .post,
                                body: LoginRedemptionRequest(redemptionToken: redemptionToken),
                                idempotencyKey: "login-redeem-\(login.id)"
                            )
                            await sessionController.install(token: redeemed.accessToken)
                            await MainActor.run { self.onCampusGateComplete?() }
                            break
                        }
                        if ["TIMEOUT", "CANCELLED", "FAILED"].contains(current.status) { self.phase = .failed(current.errorCategory ?? "认证未完成"); break }
                    } catch { self.phase = .failed(error.localizedDescription); break }
                    try? await Task.sleep(for: .seconds(2))
                }
                self.polling = nil
            }
        } catch { phase = .failed(error.localizedDescription) }
    }
    /// 取消轮询并回到 intro，供「跳过 / 稍后再说」使用。
    func cancelPolling() {
        polling?.cancel()
        polling = nil
        phase = .intro
    }

    #if DEV_AUTH
    func completeDemo(api: APIClient) async {
        guard case let .waiting(login) = phase else { return }
        do {
            guard let redemptionToken = login.redemptionToken else {
                phase = .failed("登录兑换凭证已丢失")
                return
            }
            let _: [String: JSONValue] = try await api.send(
                "/auth/session/\(login.id)/demo-complete",
                method: .post,
                body: EmptyRequest(),
                headers: ["X-Login-Redemption": redemptionToken]
            )
        } catch { phase = .failed(error.localizedDescription) }
    }
    #endif
    deinit { polling?.cancel() }

    private static func argumentValue(_ key: String, in arguments: [String]) -> String? {
        guard let index = arguments.firstIndex(of: key),
              arguments.indices.contains(index + 1) else { return nil }
        return arguments[index + 1]
    }
}

/// A3 · 统一身份认证（扫码）。
/// - `campusGateOnly`：只核验、不兑换会话（旧闸门）
/// - `bindMode`：已登录用户绑定校园身份，兑换后回调继续首次设置
struct RealLoginView: View {
    var campusGateOnly = false
    var bindMode = false
    var onCampusGateComplete: (() -> Void)? = nil
    var onSkip: (() -> Void)? = nil
    @StateObject private var model = RealLoginViewModel()
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        VStack(spacing: 0) {
            Text(bindMode || campusGateOnly ? "绑定校园身份" : "统一身份认证")
                .font(OMTheme.TypeToken.title2)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .multilineTextAlignment(.center)
                .padding(.top, OMTheme.Spacing.s4)
                .padding(.horizontal, 24)
            Text(phaseSubtitle)
                .font(OMTheme.TypeToken.footnote)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 28)
                .padding(.top, 6)

            Spacer(minLength: 8)
            phaseHero
            Spacer(minLength: 8)

            VStack(spacing: 10) {
                phaseActions
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 34)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(OMPageBackground())
        // 只用 identifier，避免 accessibility contain 把页面收成中间竖条。
        .accessibilityIdentifier("screen-A3-real-login")
    }

    private var canSkip: Bool { onSkip != nil }

    private var phaseSubtitle: String {
        switch model.phase {
        case .intro:
            if bindMode { return "用企业微信扫码，把校园身份绑到当前账号，解锁课表等校园能力" }
            if campusGateOnly { return "先用企业微信扫码完成校园核验，下一步再用手机号登录" }
            return "使用企业微信或企业邮箱扫码完成认证"
        case .creating:
            return "正在创建认证会话…"
        case .waiting:
            return "打开企业微信，扫一扫"
        case .failed:
            return "这次没连上，可以重试或稍后再说"
        }
    }

    @ViewBuilder
    private var phaseHero: some View {
        switch model.phase {
        case .intro:
            LuluView(clip: .homeIdle, placement: .hero)
                .frame(maxWidth: .infinity)
                .frame(height: 260)
        case .creating:
            CampusAuthQRLoadingSlot(message: "正在创建认证会话…")
        case let .waiting(login):
            waitingHero(login)
        case .failed:
            LuluView(clip: .coreCare, placement: .hero)
                .frame(maxWidth: .infinity)
                .frame(height: 220)
        }
    }

    @ViewBuilder
    private var phaseActions: some View {
        switch model.phase {
        case .intro:
            OMButton(bindMode || campusGateOnly ? "生成绑定二维码" : "生成认证二维码", systemIcon: "qrcode") {
                model.campusGateOnly = campusGateOnly && !bindMode
                model.onCampusGateComplete = onCampusGateComplete
                Task { await model.start(api: environment.api, sessionController: environment.session, router: router) }
            }
            .accessibilityIdentifier("auth-start-button")
            if canSkip { skipButton }
        case .creating:
            if canSkip { skipButton }
        case let .waiting(login):
            waitingActions(login)
            if canSkip { skipButton }
        case let .failed(message):
            OMCard {
                OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                    model.phase = .intro
                }
            }
            if canSkip { skipButton }
        }
    }

    private var skipButton: some View {
        OMButton(bindMode ? "跳过，稍后再绑定" : "跳过", kind: .ghost) {
            model.cancelPolling()
            onSkip?()
        }
        .accessibilityIdentifier("campus-bind-skip")
    }

    @ViewBuilder
    private func waitingHero(_ login: LoginSession) -> some View {
        let ready = Self.isQRReady(login)
        if ready, let image = qr(login.qrImageDataUrl) {
            image.resizable().interpolation(.none).scaledToFit()
                .frame(width: 220, height: 220)
                .padding(12)
                .background(OMTheme.ColorToken.card, in: RoundedRectangle(cornerRadius: OMTheme.Radius.large))
                .overlay {
                    RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                        .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                }
                .transition(.opacity.combined(with: .scale(scale: 0.98)))
        } else {
            CampusAuthQRLoadingSlot(message: Self.loadingMessage(for: login.status))
        }
    }

    @ViewBuilder
    private func waitingActions(_ login: LoginSession) -> some View {
        if Self.isQRReady(login) {
            HStack {
                Spacer(minLength: 0)
                OMChip(text: Self.statusLabel(login.status), kind: .solid)
                Spacer(minLength: 0)
            }
        }
        #if DEV_AUTH
        OMButton("开发环境：完成扫码", small: true, fillsWidth: false) {
            Task {
                if campusGateOnly {
                    onCampusGateComplete?()
                } else {
                    await model.completeDemo(api: environment.api)
                }
            }
        }
        .accessibilityIdentifier("demo-complete-login")
        #endif
    }

    /// PENDING / 尚无可用二维码时只展示加载态，避免假 QR 误导扫码。
    private static func isQRReady(_ login: LoginSession) -> Bool {
        let status = login.status.uppercased()
        guard status == "WAITING_SCAN" || status == "SCANNED" || status == "SUCCESS" else {
            return false
        }
        guard let url = login.qrImageDataUrl, url.contains(","), url.count > 32 else {
            return false
        }
        return true
    }

    private static func loadingMessage(for status: String) -> String {
        switch status.uppercased() {
        case "PENDING":
            return "正在生成核验二维码…"
        case "WAITING_SCAN":
            return "二维码准备中…"
        default:
            return "正在同步认证状态…"
        }
    }

    private static func statusLabel(_ status: String) -> String {
        switch status.uppercased() {
        case "WAITING_SCAN": return "待扫码"
        case "SCANNED": return "已扫码，请确认"
        case "SUCCESS": return "认证成功"
        case "PENDING": return "准备中"
        default: return status
        }
    }

    private func qr(_ value: String?) -> Image? {
        guard let value,
              let comma = value.firstIndex(of: ","),
              let data = Data(base64Encoded: String(value[value.index(after: comma)...])),
              let image = UIImage(data: data) else { return nil }
        return Image(uiImage: image)
    }
}

/// PENDING 阶段的二维码占位：脉冲边框 + 进度，不展示可扫的假码。
private struct CampusAuthQRLoadingSlot: View {
    let message: String
    @State private var pulse = false

    var body: some View {
        VStack(spacing: 16) {
            ZStack {
                RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                    .fill(OMTheme.ColorToken.card)
                    .frame(width: 244, height: 244)
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .overlay {
                        RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                            .stroke(OMTheme.ColorToken.sage.opacity(pulse ? 0.55 : 0.15), lineWidth: 2)
                            .padding(3)
                    }
                    .shadow(color: OMTheme.ColorToken.ink.opacity(pulse ? 0.06 : 0.02), radius: pulse ? 16 : 6, y: 4)

                VStack(spacing: 14) {
                    ProgressView()
                        .controlSize(.large)
                        .tint(OMTheme.ColorToken.ink)
                    Text(message)
                        .font(OMTheme.TypeToken.callout.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal, 20)
                }
            }
            .accessibilityElement(children: .combine)
            .accessibilityLabel(message)
            .accessibilityIdentifier("campus-auth-qr-loading")

            OMChip(text: "准备中", kind: .soft)
        }
        .onAppear {
            withAnimation(.easeInOut(duration: 1.1).repeatForever(autoreverses: true)) {
                pulse = true
            }
        }
    }
}
