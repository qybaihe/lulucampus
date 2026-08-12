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
                                self.onCampusGateComplete?()
                                break
                            }
                            let redeemed: LoginRedemptionResult = try await api.send(
                                "/auth/session/\(login.id)/redeem",
                                method: .post,
                                body: LoginRedemptionRequest(redemptionToken: redemptionToken),
                                idempotencyKey: "login-redeem-\(login.id)"
                            )
                            await sessionController.install(token: redeemed.accessToken)
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

/// A3 · 统一身份认证（扫码）。`campusGateOnly` 时只核验中大身份，不兑换登录会话。
struct RealLoginView: View {
    var campusGateOnly = false
    var onCampusGateComplete: (() -> Void)? = nil
    @StateObject private var model = RealLoginViewModel()
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        VStack(spacing: 20) {
            Spacer(minLength: 0)
            LuluView(clip: .homeIdle, placement: .empty).frame(height: 205)
            Text(campusGateOnly ? "中大校园认证" : "统一身份认证")
                .font(OMTheme.TypeToken.hero)
                .tracking(-0.7)
                .foregroundStyle(OMTheme.ColorToken.ink)
            switch model.phase {
            case .intro:
                Text(campusGateOnly
                     ? "先用企业微信扫码完成校园核验，下一步再用手机号登录"
                     : "使用企业微信或企业邮箱扫码完成认证")
                    .font(OMTheme.TypeToken.callout)
                    .multilineTextAlignment(.center)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.horizontal, 30)
                OMButton(campusGateOnly ? "生成校园核验二维码" : "生成认证二维码", systemIcon: "qrcode") {
                    model.campusGateOnly = campusGateOnly
                    model.onCampusGateComplete = onCampusGateComplete
                    Task { await model.start(api: environment.api, sessionController: environment.session, router: router) }
                }
                .padding(.horizontal, 24)
                .accessibilityIdentifier("auth-start-button")
            case .creating:
                CampusAuthQRLoadingSlot(message: "正在创建认证会话…")
            case let .waiting(login):
                waitingContent(login)
            case let .failed(message):
                OMCard {
                    OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                        model.phase = .intro
                    }
                }
                .padding(.horizontal, 24)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(OMPageBackground())
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-A3-real-login")
    }

    @ViewBuilder
    private func waitingContent(_ login: LoginSession) -> some View {
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
            OMChip(text: Self.statusLabel(login.status), kind: .solid)
            Text("请使用企业微信扫码")
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.horizontal, 30)
        } else {
            CampusAuthQRLoadingSlot(message: Self.loadingMessage(for: login.status))
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
