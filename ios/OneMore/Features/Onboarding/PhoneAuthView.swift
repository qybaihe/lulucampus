import SwiftUI

/// 手机号 + 密码登录 / 注册（所有学校最终都落到这里）。
struct PhoneAuthView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var mode: Mode = .login
    @State private var phone = ""
    @State private var password = ""
    @State private var displayName = ""
    @State private var working = false
    @State private var error: String?

    enum Mode: String, CaseIterable { case login = "登录"; case register = "注册" }

    private var phoneValid: Bool {
        phone.range(of: #"^1[3-9]\d{9}$"#, options: .regularExpression) != nil
    }
    private var passwordValid: Bool { (6...64).contains(password.count) }
    private var canSubmit: Bool { phoneValid && passwordValid && !working }

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                LuluView(clip: .homeReply, placement: .header)
                    .frame(height: 120)
                    .padding(.top, OMTheme.Spacing.s3)
                Text(mode == .login ? "欢迎回来" : "创建账号")
                    .font(OMTheme.TypeToken.title2)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s3)
                Text(mode == .login ? "手机号与密码登录" : "一分钟注册，差一个就成局")
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.top, 4)

                HStack(spacing: 8) {
                    ForEach(Mode.allCases, id: \.self) { item in
                        Button {
                            mode = item
                            error = nil
                        } label: {
                            Text(item.rawValue)
                                .font(OMTheme.TypeToken.footnote.weight(.semibold))
                                .foregroundStyle(mode == item ? OMTheme.ColorToken.card : OMTheme.ColorToken.ink)
                                .padding(.horizontal, 16)
                                .frame(minHeight: 32)
                                .background(mode == item ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
                                .clipShape(Capsule())
                                .overlay {
                                    Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                                }
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, OMTheme.Spacing.s4)

                OMCard {
                    Text("手机号").font(OMTheme.TypeToken.caption).foregroundStyle(OMTheme.ColorToken.mist)
                    TextField("11 位手机号", text: $phone)
                        .keyboardType(.numberPad)
                        .textContentType(.telephoneNumber)
                        .modifier(OMInputStyle())
                        .padding(.top, 4)
                        .onChange(of: phone) { _, value in
                            phone = String(value.filter(\.isNumber).prefix(11))
                        }
                        .accessibilityIdentifier("phone-auth-phone")

                    Text("密码")
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                        .padding(.top, OMTheme.Spacing.s3)
                    SecureField(mode == .register ? "6–64 位密码" : "输入密码", text: $password)
                        .textContentType(mode == .register ? .newPassword : .password)
                        .modifier(OMInputStyle())
                        .padding(.top, 4)
                        .accessibilityIdentifier("phone-auth-password")

                    if mode == .register {
                        Text("昵称（可选）")
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .padding(.top, OMTheme.Spacing.s3)
                        TextField("不填则默认同学+尾号", text: $displayName)
                            .modifier(OMInputStyle())
                            .padding(.top, 4)
                    }
                }
                .padding(.top, OMTheme.Spacing.s3)

                if let error {
                    Text(error)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(Color.red.opacity(0.85))
                        .padding(.top, OMTheme.Spacing.s2)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }

                OMButton(
                    working ? (mode == .register ? "注册中…" : "登录中…") : (mode == .register ? "注册并进入" : "登录"),
                    loading: working,
                    disabledReason: canSubmit ? nil : (phoneValid ? "请填写有效密码" : "请输入 11 位手机号")
                ) {
                    Task { await submit() }
                }
                .padding(.top, OMTheme.Spacing.s4)
                .accessibilityIdentifier("phone-auth-submit")
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("screen-A2b-phone-auth")
    }

    private func submit() async {
        guard canSubmit else {
            if !phoneValid { error = "请输入 11 位大陆手机号" }
            else if !passwordValid { error = "密码长度需在 6–64 位之间" }
            return
        }
        working = true
        error = nil
        defer { working = false }
        do {
            let result: PhoneAuthResult
            if mode == .register {
                let name = displayName.trimmingCharacters(in: .whitespaces)
                result = try await environment.identity.registerPhone(
                    phone: phone,
                    password: password,
                    displayName: name.isEmpty ? nil : name
                )
            } else {
                result = try await environment.identity.loginPhone(phone: phone, password: password)
            }
            await environment.session.install(token: result.accessToken, needsOnboarding: result.isNewUser ? true : nil)
        } catch {
            self.error = error.localizedDescription
        }
    }
}
