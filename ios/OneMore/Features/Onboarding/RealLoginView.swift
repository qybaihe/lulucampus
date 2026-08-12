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
            Spacer()
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
                OMCard { OMG5StateView(state: .loading, message: "正在创建认证会话…") }
                    .padding(.horizontal, 24)
            case let .waiting(login):
                if let image = qr(login.qrImageDataUrl) {
                    image.resizable().interpolation(.none).scaledToFit()
                        .frame(width: 220, height: 220)
                        .padding(12)
                        .background(OMTheme.ColorToken.card, in: RoundedRectangle(cornerRadius: OMTheme.Radius.large))
                        .overlay {
                            RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                } else {
                    OMQRPattern()
                        .frame(width: 180, height: 180)
                        .padding(20)
                        .background(OMTheme.ColorToken.card, in: RoundedRectangle(cornerRadius: OMTheme.Radius.large))
                        .overlay {
                            RoundedRectangle(cornerRadius: OMTheme.Radius.large)
                                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                }
                OMChip(text: login.status, kind: .solid)
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
            case let .failed(message):
                OMCard {
                    OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                        model.phase = .intro
                    }
                }
                .padding(.horizontal, 24)
            }
            Spacer()
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-A3-real-login")
    }
    private func qr(_ value: String?) -> Image? { guard let value, let comma = value.firstIndex(of: ","), let data = Data(base64Encoded: String(value[value.index(after: comma)...])), let image = UIImage(data: data) else { return nil }; return Image(uiImage: image) }
}
