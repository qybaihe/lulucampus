import Foundation

enum WebSocketClientError: LocalizedError, Equatable, Sendable {
    case notConnected
    case sessionExpired

    var errorDescription: String? {
        switch self {
        case .notConnected: "消息连接尚未建立，请稍后重试"
        case .sessionExpired: "登录已失效，请重新认证"
        }
    }
}

actor WebSocketClient {
    enum State: Equatable, Sendable { case idle, connecting, connected, waitingToRetry(Int) }
    private let baseURL: URL
    private let auth: AuthManager
    private let session: URLSession
    private var task: URLSessionWebSocketTask?
    private var receiveTask: Task<Void, Never>?
    private var seenMessageIDs = Set<String>()
    private var isForeground = true
    private(set) var state: State = .idle

    init(baseURL: URL, auth: AuthManager, session: URLSession = .shared) {
        self.baseURL = baseURL; self.auth = auth; self.session = session
    }

    func messages(channelID: String) -> AsyncStream<MessagePayload> {
        AsyncStream { continuation in
            receiveTask?.cancel()
            receiveTask = Task { [weak self] in
                guard let self else { return }
                await self.connectLoop(channelID: channelID, continuation: continuation)
            }
            continuation.onTermination = { [weak self] _ in Task { await self?.disconnect() } }
        }
    }

    private func connectLoop(channelID: String, continuation: AsyncStream<MessagePayload>.Continuation) async {
        var retry = 0
        while !Task.isCancelled {
            while !isForeground && !Task.isCancelled {
                state = .idle
                try? await Task.sleep(for: .milliseconds(250))
            }
            if Task.isCancelled { break }
            let headers = await auth.headers()
            guard !headers.isEmpty else { continuation.finish(); return }
            let url = baseURL.appending(path: "/channels/\(channelID)")
            var request = URLRequest(url: url)
            for (name, value) in headers { request.setValue(value, forHTTPHeaderField: name) }
            state = .connecting
            let socket = session.webSocketTask(with: request)
            task = socket; socket.resume(); state = .connected
            do {
                while !Task.isCancelled {
                    let incoming = try await socket.receive()
                    retry = 0
                    let data: Data
                    switch incoming { case let .data(value): data = value; case let .string(value): data = Data(value.utf8); @unknown default: continue }
                    let message = try JSONDecoder.oneMore.decode(MessagePayload.self, from: data)
                    if seenMessageIDs.insert(message.id).inserted { continuation.yield(message) }
                }
            } catch {
                if socket.closeCode.rawValue == 4401 {
                    await auth.markExpired()
                    await MainActor.run { NotificationCenter.default.post(name: .oneMoreSessionExpired, object: nil) }
                    continuation.finish()
                    return
                }
                if !isForeground { continue }
                retry += 1; state = .waitingToRetry(retry)
                try? await Task.sleep(for: .seconds(min(pow(2.0, Double(retry)), 20)))
            }
        }
        continuation.finish()
    }

    func send(_ body: Data) async throws {
        guard let task, state == .connected else { throw WebSocketClientError.notConnected }
        try await task.send(.data(body))
    }

    func setForeground(_ foreground: Bool) {
        isForeground = foreground
        if !foreground {
            task?.cancel(with: .goingAway, reason: nil)
            task = nil
            state = .idle
        }
    }

    func disconnect() {
        receiveTask?.cancel(); receiveTask = nil
        task?.cancel(with: .goingAway, reason: nil); task = nil; state = .idle
    }
}
