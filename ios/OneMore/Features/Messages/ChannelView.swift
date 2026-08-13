import SwiftUI
import UIKit

@MainActor final class ChannelViewModel: ObservableObject {
    @Published var messages: [MessagePayload] = []
    @Published var draft = ""
    @Published var error: String?
    @Published var sending = false
    @Published var scenePolicy: ChannelScenePolicy?
    private var boundaryTask: Task<Void, Never>?
    private let channelID: String; private let social: SocialRepository; private let socket: WebSocketClient
    init(channelID: String, social: SocialRepository, socket: WebSocketClient) { self.channelID = channelID; self.social = social; self.socket = socket }
    func connect() async {
        do {
            scenePolicy = try await social.channelScenePolicy(channelID: channelID)
            messages = try await social.messages(channelID: channelID)
        } catch {
            self.error = error.localizedDescription
            return
        }
        schedulePolicyBoundary()
        guard scenePolicy?.liveConnectionEnabled == true else { return }
        for await message in await socket.messages(channelID: channelID) where !messages.contains(where: { $0.id == message.id }) { messages.append(message) }
    }
    func refreshPolicy() async {
        await socket.disconnect()
        await connect()
    }
    private func schedulePolicyBoundary() {
        boundaryTask?.cancel()
        guard let next = scenePolicy?.nextChangeAt, next > .now else { return }
        boundaryTask = Task { [weak self] in
            let delay = max(0, next.timeIntervalSinceNow + 0.25)
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled, let self else { return }
            await self.refreshPolicy()
        }
    }
    deinit { boundaryTask?.cancel() }
    func send() async -> Bool {
        let value = draft.trimmingCharacters(in: .whitespacesAndNewlines); guard !value.isEmpty, !sending else { return false }
        sending = true; defer { sending = false }
        do { let message = try await social.sendText(channelID: channelID, text: value); if !messages.contains(where: { $0.id == message.id }) { messages.append(message) }; draft = ""; error = nil; Task { await self.pullCastReplies() }; return true }
        catch { self.error = error.localizedDescription; return false }
    }
    /// 演示人物回消息有 3–11 秒延迟；WebSocket 漏了就再拉几次。
    private func pullCastReplies() async {
        for delay in [5.0, 7.0, 10.0] {
            try? await Task.sleep(for: .seconds(delay))
            guard !Task.isCancelled else { return }
            guard let latest = try? await social.messages(channelID: channelID) else { continue }
            for item in latest where !messages.contains(where: { $0.id == item.id }) {
                messages.append(item)
            }
            messages.sort { $0.sentAt < $1.sentAt }
        }
    }
    func mentionAzou() async -> Bool {
        let value = draft.trimmingCharacters(in: .whitespacesAndNewlines); guard !value.isEmpty, !sending else { return false }
        sending = true; defer { sending = false }
        do {
            let result = try await social.mentionAzou(channelID: channelID, text: value)
            if !messages.contains(where: { $0.id == result.message.id }) { messages.append(result.message) }
            draft = ""; error = nil; return true
        } catch { self.error = error.localizedDescription; return false }
    }
    func sendImage(_ data: Data) async {
        guard !sending else { return }; sending = true; defer { sending = false }
        let image = UIImage(data: data)
        do { let message = try await social.uploadAndSendImage(channelID: channelID, data: data, width: image.map { Int($0.size.width * $0.scale) }, height: image.map { Int($0.size.height * $0.scale) }, caption: "图片"); if !messages.contains(where: { $0.id == message.id }) { messages.append(message) }; error = nil }
        catch { self.error = error.localizedDescription }
    }
    func sendLocation(latitude: Double, longitude: Double) async {
        guard !sending else { return }; sending = true; defer { sending = false }
        do { let message = try await social.sendLocation(channelID: channelID, latitude: latitude, longitude: longitude, label: "我发送的位置"); if !messages.contains(where: { $0.id == message.id }) { messages.append(message) }; error = nil }
        catch { self.error = error.localizedDescription }
    }
}

/// E14 · 局内群聊。无已读回执、无在线状态；噜噜只在自己开口时出镜，不常驻。
struct ChannelView: View {
    @StateObject private var model: ChannelViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @State private var showPhotos = false
    @State private var currentUserID: String?
    init(channelID: String, social: SocialRepository, socket: WebSocketClient) { _model = StateObject(wrappedValue: ChannelViewModel(channelID: channelID, social: social, socket: socket)) }

    var body: some View {
        VStack(spacing: 0) {
            if let error = model.error {
                Text(error)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.vertical, 8)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(OMTheme.ColorToken.gapSoft)
            }
            if let policy = model.scenePolicy, !policy.sendingEnabled {
                VStack(alignment: .leading, spacing: 5) {
                    HStack(spacing: 8) {
                        Image(om: .shield).font(.system(size: 15))
                        Text("现场禁言").font(OMTheme.TypeToken.callout.weight(.semibold))
                    }
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    Text(policy.reason ?? "此场景现场不提供连接")
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                    if let next = policy.nextChangeAt {
                        Text("结束后 \(next.formatted(date: .omitted, time: .shortened)) 可继续复盘")
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    OMButton("刷新场景状态", kind: .ghost, small: true, fillsWidth: false) {
                        Task { await model.refreshPolicy() }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(OMTheme.Spacing.s4)
                .background(OMTheme.ColorToken.card)
                .overlay(alignment: .bottom) {
                    Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
                }
                .accessibilityIdentifier("scene-sensitive-muted")
            }
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(model.messages) { message in
                            bubble(message).id(message.id)
                        }
                    }
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.vertical, 12)
                }
                .onChange(of: model.messages.count) { _, _ in
                    if let last = model.messages.last {
                        withAnimation { proxy.scrollTo(last.id, anchor: .bottom) }
                    }
                }
            }
            if model.scenePolicy?.sendingEnabled == true {
                inputBar
            }
            OMPermissionRecoveryNotice(coordinator: environment.permissions, permissions: [.photos, .location])
                .padding(.horizontal, OMTheme.Spacing.pageX)
        }
        .background(OMPageBackground())
        .task {
            currentUserID = await environment.auth.currentUserID()
            await model.connect()
        }
        .sheet(isPresented: $showPhotos) { PhotoPicker { data in Task { await model.sendImage(data) } } }
        .onChange(of: environment.permissions.location) { _, value in
            if let value {
                Task { await model.sendLocation(latitude: value.coordinate.latitude, longitude: value.coordinate.longitude) }
            }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-E14-channel")
    }

    private var inputBar: some View {
        HStack(spacing: 8) {
            OMIconButton(icon: .doc, size: 38, accessibilityLabel: "发送图片") {
                Task { if await environment.permissions.requestPhotoSelection() { showPhotos = true } }
            }
            OMIconButton(icon: .pin, size: 38, accessibilityLabel: "发送一次位置") {
                environment.permissions.requestOneShotLocation()
            }
            TextField("消息（无已读/在线/输入中）", text: $model.draft, axis: .vertical)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .padding(.horizontal, 18)
                .frame(minHeight: 42)
                .background(OMTheme.ColorToken.card)
                .clipShape(Capsule())
                .overlay { Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
                .accessibilityIdentifier("channel-message-input")
            OMIconButton(icon: .arrow, size: 42, accessibilityLabel: "发送消息") {
                Task { await sendDraft() }
            }
            .opacity(model.sending || model.draft.trimmingCharacters(in: .whitespaces).isEmpty ? 0.45 : 1)
            .disabled(model.sending || model.draft.trimmingCharacters(in: .whitespaces).isEmpty)
            .accessibilityIdentifier("channel-send-message")
        }
        .padding(.horizontal, OMTheme.Spacing.pageX)
        .padding(.top, 10)
        .padding(.bottom, 12)
        .background(OMTheme.ColorToken.card)
        .overlay(alignment: .top) {
            Rectangle().fill(OMTheme.ColorToken.line).frame(height: OMTheme.Radius.borderWidth)
        }
    }

    private func sendDraft() async {
        let isMention = model.draft.localizedCaseInsensitiveContains("@Lulu") || model.draft.contains("@噜噜")
        if isMention {
            environment.motion.trigger(.azouMentioned)
            if await model.mentionAzou() { environment.motion.trigger(.azouResponseCompleted) }
        } else if await model.send() {
            environment.motion.trigger(.humanConversationStarted)
        }
    }

    @ViewBuilder private func bubble(_ message: MessagePayload) -> some View {
        if message.senderType == "system" {
            systemCard(message)
        } else if message.senderType == "azou" {
            luluBubble(message)
        } else {
            humanBubble(message)
        }
    }

    /// 水豚噜噜站在左边，旁边跟一条开口气泡。
    private func luluBubble(_ message: MessagePayload) -> some View {
        HStack(alignment: .top, spacing: 4) {
            LuluView(clip: .homeReply, placement: .chat)
                .accessibilityHidden(true)
                .padding(.top, 2)
            VStack(alignment: .leading, spacing: 4) {
                Text(AppBrand.mascotName)
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.leading, 6)
                HStack(alignment: .top, spacing: 0) {
                    LuluChatBubbleTail()
                        .fill(OMTheme.ColorToken.gapSoft)
                        .frame(width: 8, height: 10)
                        .padding(.top, 12)
                        .offset(x: 1)
                    VStack(alignment: .leading, spacing: 5) {
                        if let content = message.content {
                            Text(content)
                                .font(OMTheme.TypeToken.callout)
                                .lineSpacing(3)
                        }
                        Text(message.sentAt.formatted(date: .omitted, time: .shortened))
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 10)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .background(OMTheme.ColorToken.gapSoft)
                    .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 18, style: .continuous)
                            .stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth)
                    }
                }
            }
            Spacer(minLength: 36)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("channel-lulu-bubble")
    }

    /// G · 入群第一眼的「成局卡」：系统一次性事实摘要，之后 AI 闭嘴。
    private func systemCard(_ message: MessagePayload) -> some View {
        let lines = (message.content ?? "").split(separator: "\n").map(String.init)
        return VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                OMSticker("round-table.png", size: .s44)
                Text(lines.first ?? "成局卡")
                    .font(OMTheme.TypeToken.callout.weight(.bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer()
            }
            ForEach(Array(lines.dropFirst().enumerated()), id: \.offset) { _, line in
                Text(line)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .lineSpacing(2)
            }
            Text("以上是系统整理的事实摘要 · 接下来交给你们")
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
                .padding(.top, 2)
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(OMTheme.ColorToken.gapSoft)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(OMTheme.ColorToken.yolkBorder, lineWidth: OMTheme.Radius.borderWidth)
        }
        .accessibilityElement(children: .combine)
        .accessibilityIdentifier("channel-system-gathering-card")
    }

    private func humanBubble(_ message: MessagePayload) -> some View {
        let isMine = message.senderType == "human" && message.senderId == currentUserID
        return HStack(alignment: .top, spacing: 0) {
            if isMine { Spacer(minLength: 44) }
            VStack(alignment: .leading, spacing: 5) {
                if !isMine {
                    Text(message.senderDisplayName ?? "同学")
                        .font(OMTheme.TypeToken.caption.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                if let content = message.content {
                    Text(content)
                        .font(OMTheme.TypeToken.callout)
                        .lineSpacing(3)
                }
                if let location = message.location {
                    Label(location.label, systemImage: "mappin.and.ellipse")
                        .font(OMTheme.TypeToken.footnote)
                }
                if let image = message.image {
                    AuthenticatedMessageImage(image: image, api: environment.api)
                }
                Text(message.sentAt.formatted(date: .omitted, time: .shortened))
                    .font(OMTheme.TypeToken.caption)
                    .foregroundStyle(isMine ? OMTheme.ColorToken.paper.opacity(0.7) : OMTheme.ColorToken.mist)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 10)
            .foregroundStyle(isMine ? OMTheme.ColorToken.paper : OMTheme.ColorToken.ink)
            .background(isMine ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
            .overlay {
                RoundedRectangle(cornerRadius: 18, style: .continuous)
                    .stroke(isMine ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
            }
            if !isMine { Spacer(minLength: 44) }
        }
        .accessibilityElement(children: .combine)
    }
}

private struct LuluChatBubbleTail: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: rect.maxX, y: 0))
        path.addQuadCurve(
            to: CGPoint(x: rect.minX, y: rect.midY),
            control: CGPoint(x: rect.midX, y: rect.midY - 1)
        )
        path.addQuadCurve(
            to: CGPoint(x: rect.maxX, y: rect.maxY),
            control: CGPoint(x: rect.midX, y: rect.midY + 1)
        )
        path.closeSubpath()
        return path
    }
}

private struct AuthenticatedMessageImage: View {
    enum Phase { case loading, loaded(UIImage), failed(String) }
    let image: MessagePayload.Image
    let api: APIClient
    @State private var phase: Phase = .loading
    @State private var reloadID = UUID()

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            switch phase {
            case .loading:
                RoundedRectangle(cornerRadius: 12).fill(OMTheme.ColorToken.readySoft)
                    .frame(width: 210, height: 150)
                    .overlay { ProgressView().tint(OMTheme.ColorToken.ink) }
            case let .loaded(value):
                Image(uiImage: value).resizable().scaledToFill()
                    .frame(width: 210, height: 150)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .accessibilityLabel(image.caption ?? "聊天图片")
            case let .failed(message):
                VStack(alignment: .leading, spacing: 6) {
                    Label("图片暂不可查看", systemImage: "photo.badge.exclamationmark")
                    Text(message).font(OMTheme.TypeToken.caption).foregroundStyle(OMTheme.ColorToken.mist)
                    OMButton("重试图片", kind: .ghost, small: true, fillsWidth: false) {
                        phase = .loading
                        reloadID = UUID()
                    }
                }
                .frame(width: 210, alignment: .leading)
            }
            if let caption = image.caption {
                Text(caption).font(OMTheme.TypeToken.footnote)
            }
        }
        .task(id: reloadID) {
            do {
                let data = try await api.authenticatedImage(image.url)
                guard let decoded = UIImage(data: data) else { throw APIClientError.invalidResponse }
                phase = .loaded(decoded)
            } catch { phase = .failed(error.localizedDescription) }
        }
        .accessibilityIdentifier("authenticated-message-image")
    }
}
