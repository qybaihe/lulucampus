import Foundation
import CryptoKit

actor IdempotencyKeyJournal {
    private struct Entry: Codable { let key: String; let createdAt: Date }
    private var entries: [String: Entry] = [:]
    private let keychain: KeychainStore
    private let account = "pending-write-keys-v1"

    init(keychain: KeychainStore = .init(service: "com.onemore.campus.idempotency")) {
        self.keychain = keychain
        if let raw = keychain.read(account: account),
           let data = raw.data(using: .utf8),
           let decoded = try? JSONDecoder().decode([String: Entry].self, from: data) {
            entries = decoded
        }
    }

    func key(for fingerprint: String, proposed: String) -> String {
        let cutoff = Date().addingTimeInterval(-7 * 86_400)
        entries = entries.filter { $0.value.createdAt >= cutoff }
        if let existing = entries[fingerprint] { persist(); return existing.key }
        entries[fingerprint] = Entry(key: proposed, createdAt: .now)
        persist()
        return proposed
    }

    func complete(_ fingerprint: String) {
        entries.removeValue(forKey: fingerprint)
        persist()
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        keychain.write(String(decoding: data, as: UTF8.self), account: account)
    }
}

actor PendingMutationJournal {
    enum State: String, Codable, Sendable, Equatable { case pending, ambiguous, needsAttention }
    struct Entry: Codable, Identifiable, Sendable, Equatable {
        let id: String
        let scope: String
        let path: String
        let method: String
        let body: Data
        let idempotencyKey: String
        let createdAt: Date
        var state: State
        var lastErrorCode: String?
    }

    private var entries: [Entry] = []
    private let keychain: KeychainStore
    private let account = "pending-mutations-v1"

    init(keychain: KeychainStore = .init(service: "com.onemore.campus.pending-writes")) {
        self.keychain = keychain
        if let raw = keychain.read(account: account),
           let data = raw.data(using: .utf8),
           let decoded = try? JSONDecoder().decode([Entry].self, from: data) {
            entries = decoded
        }
    }

    func enqueue(
        scope: String,
        path: String,
        method: HTTPMethod,
        body: Data,
        idempotencyKey: String,
        state: State = .pending,
        errorCode: String? = nil
    ) {
        guard body.count <= 256 * 1_024 else { return }
        if let index = entries.firstIndex(where: {
            $0.scope == scope && $0.method == method.rawValue
                && $0.path == path && $0.idempotencyKey == idempotencyKey
        }) {
            entries[index].state = state
            entries[index].lastErrorCode = errorCode
        } else {
            entries.append(
                Entry(
                    id: UUID().uuidString,
                    scope: scope,
                    path: path,
                    method: method.rawValue,
                    body: body,
                    idempotencyKey: idempotencyKey,
                    createdAt: .now,
                    state: state,
                    lastErrorCode: errorCode
                )
            )
        }
        entries = Array(entries.suffix(100))
        persist()
    }

    func entries(scope: String) -> [Entry] { entries.filter { $0.scope == scope } }

    func complete(_ id: String) {
        entries.removeAll { $0.id == id }
        persist()
    }

    func complete(
        scope: String,
        path: String,
        method: HTTPMethod,
        idempotencyKey: String
    ) {
        entries.removeAll {
            $0.scope == scope && $0.path == path && $0.method == method.rawValue
                && $0.idempotencyKey == idempotencyKey
        }
        persist()
    }

    func update(_ id: String, state: State, errorCode: String?) {
        guard let index = entries.firstIndex(where: { $0.id == id }) else { return }
        entries[index].state = state
        entries[index].lastErrorCode = errorCode
        persist()
    }

    func removeAll() {
        entries.removeAll()
        persist()
    }

    private func persist() {
        guard let data = try? JSONEncoder().encode(entries) else { return }
        keychain.write(String(decoding: data, as: UTF8.self), account: account)
    }
}

actor NetworkDiagnostics {
    private(set) var lastRequestID: String?
    private(set) var lastPath: String?

    func record(requestID: String?, path: String) {
        lastRequestID = requestID
        lastPath = path
    }

    func snapshot() -> (String?, String?) { (lastRequestID, lastPath) }
}

actor APIClient {
    let baseURL: URL
    private let session: URLSession
    private let auth: AuthManager
    let diagnostics: NetworkDiagnostics
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let cache: any ResponseCaching
    private let imageCache = NSCache<NSString, NSData>()
    private let idempotencyJournal: IdempotencyKeyJournal
    private let mutationJournal: PendingMutationJournal
    private let network: any NetworkAvailabilityProviding

    init(
        baseURL: URL,
        auth: AuthManager,
        diagnostics: NetworkDiagnostics = .init(),
        session: URLSession? = nil,
        cache: any ResponseCaching = ResponseCache(),
        idempotencyJournal: IdempotencyKeyJournal = .init(),
        mutationJournal: PendingMutationJournal = .init(),
        network: any NetworkAvailabilityProviding = NetworkAvailability()
    ) {
        self.baseURL = baseURL
        self.auth = auth
        self.diagnostics = diagnostics
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 120
        configuration.waitsForConnectivity = true
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        configuration.urlCache = nil
        self.session = session ?? URLSession(configuration: configuration)
        self.cache = cache
        self.idempotencyJournal = idempotencyJournal
        self.mutationJournal = mutationJournal
        self.network = network
        imageCache.countLimit = 80
        imageCache.totalCostLimit = 24 * 1024 * 1024
        decoder = JSONDecoder.oneMore
        encoder = JSONEncoder.oneMore
    }

    func get<Response: Decodable & Sendable>(
        _ path: String,
        query: [URLQueryItem] = [],
        headers: [String: String] = [:]
    ) async throws -> Response {
        try await request(
            path,
            method: .get,
            body: Optional<EmptyRequest>.none,
            query: query,
            attempts: 2,
            extraHeaders: headers
        )
    }

    func send<Body: Encodable & Sendable, Response: Decodable & Sendable>(
        _ path: String,
        method: HTTPMethod,
        body: Body,
        idempotencyKey: String? = nil,
        query: [URLQueryItem] = [],
        headers: [String: String] = [:]
    ) async throws -> Response {
        guard let idempotencyKey else {
            return try await request(
                path,
                method: method,
                body: body,
                query: query,
                attempts: 1,
                extraHeaders: headers
            )
        }
        let bodyData = try encoder.encode(body)
        let scope = await auth.cacheScope()
        let fingerprintData = Data("\(scope)|\(method.rawValue)|\(path)|".utf8) + bodyData
        let fingerprint = SHA256.hash(data: fingerprintData).map { String(format: "%02x", $0) }.joined()
        let stableKey = await idempotencyJournal.key(for: fingerprint, proposed: idempotencyKey)
        if !(await network.online()) {
            await mutationJournal.enqueue(
                scope: scope,
                path: path,
                method: method,
                body: bodyData,
                idempotencyKey: stableKey
            )
            throw APIClientError.offline
        }
        do {
            let value: Response = try await request(
                path,
                method: method,
                body: body,
                query: query,
                attempts: 2,
                idempotencyKey: stableKey,
                extraHeaders: headers
            )
            await idempotencyJournal.complete(fingerprint)
            await mutationJournal.complete(
                scope: scope,
                path: path,
                method: method,
                idempotencyKey: stableKey
            )
            return value
        } catch let error as APIClientError {
            if case .offline = error {
                await mutationJournal.enqueue(
                    scope: scope,
                    path: path,
                    method: method,
                    body: bodyData,
                    idempotencyKey: stableKey
                )
            } else if case .transport = error {
                await mutationJournal.enqueue(
                    scope: scope,
                    path: path,
                    method: method,
                    body: bodyData,
                    idempotencyKey: stableKey
                )
            }
            if case let .server(_, body) = error,
               ["IDEMPOTENCY_IN_PROGRESS", "IDEMPOTENCY_RESULT_PENDING", "IDEMPOTENCY_RESULT_UNKNOWN"].contains(body.code) {
                await mutationJournal.enqueue(
                    scope: scope,
                    path: path,
                    method: method,
                    body: bodyData,
                    idempotencyKey: stableKey,
                    state: .ambiguous,
                    errorCode: body.code
                )
            } else if case .server = error {
                await idempotencyJournal.complete(fingerprint)
            }
            throw error
        }
    }

    func uploadImage(_ data: Data, filename: String, width: Int?, height: Int?, contentType: String = "image/jpeg") async throws -> ImageAsset {
        guard await network.online() else { throw APIClientError.offline }
        let url = baseURL.appending(path: "/media/images")
        var request = URLRequest(url: url); request.httpMethod = "POST"; request.httpBody = data
        request.setValue(contentType, forHTTPHeaderField: "Content-Type"); request.setValue(filename, forHTTPHeaderField: "X-Filename")
        if let width { request.setValue(String(width), forHTTPHeaderField: "X-Image-Width") }
        if let height { request.setValue(String(height), forHTTPHeaderField: "X-Image-Height") }
        for (name, value) in await auth.headers() { request.setValue(value, forHTTPHeaderField: name) }
        let (responseData, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIClientError.invalidResponse }
        let requestID = http.value(forHTTPHeaderField: "X-Request-ID"); await diagnostics.record(requestID: requestID, path: "/media/images")
        guard (200..<300).contains(http.statusCode) else {
            if http.statusCode == 401 {
                await auth.markExpired()
                await clearSessionData()
                await MainActor.run { NotificationCenter.default.post(name: .oneMoreSessionExpired, object: nil) }
                throw APIClientError.sessionExpired(requestID: requestID)
            }
            let error = (try? decoder.decode(APIErrorEnvelope.self, from: responseData).error) ?? APIErrorBody(code: "UPLOAD_FAILED", message: "图片上传失败", details: [:], requestId: requestID)
            throw APIClientError.server(status: http.statusCode, body: error)
        }
        return try decoder.decode(APIEnvelope<ImageAsset>.self, from: responseData).data
    }

    func authenticatedImage(_ rawURL: String) async throws -> Data {
        guard let url = URL(string: rawURL, relativeTo: baseURL)?.absoluteURL,
              url.scheme == baseURL.scheme,
              url.host == baseURL.host,
              url.port == baseURL.port,
              url.path.hasPrefix("/media/images/") else {
            throw APIClientError.invalidConfiguration
        }
        let scope = await auth.cacheScope()
        let key = "\(scope)|\(url.absoluteString)" as NSString
        if let cached = imageCache.object(forKey: key) { return cached as Data }
        guard await network.online() else { throw APIClientError.offline }
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.httpMethod = "GET"
        request.setValue("image/jpeg,image/png,image/heic,image/heif", forHTTPHeaderField: "Accept")
        request.setValue(UUID().uuidString, forHTTPHeaderField: "X-Request-ID")
        for (name, value) in await auth.headers() { request.setValue(value, forHTTPHeaderField: name) }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIClientError.invalidResponse }
        let requestID = http.value(forHTTPHeaderField: "X-Request-ID")
        await diagnostics.record(requestID: requestID, path: url.path)
        if http.statusCode == 401 {
            await auth.markExpired()
            await clearSessionData()
            await MainActor.run { NotificationCenter.default.post(name: .oneMoreSessionExpired, object: nil) }
            throw APIClientError.sessionExpired(requestID: requestID)
        }
        guard (200..<300).contains(http.statusCode) else {
            let body = (try? decoder.decode(APIErrorEnvelope.self, from: data).error)
                ?? APIErrorBody(code: "IMAGE_HTTP_\(http.statusCode)", message: "图片已不可访问", details: [:], requestId: requestID)
            throw APIClientError.server(status: http.statusCode, body: body)
        }
        guard data.count <= 24 * 1024 * 1024,
              http.value(forHTTPHeaderField: "Content-Type")?.lowercased().hasPrefix("image/") == true else {
            throw APIClientError.invalidResponse
        }
        imageCache.setObject(data as NSData, forKey: key, cost: data.count)
        return data
    }

    private func request<Body: Encodable & Sendable, Response: Decodable & Sendable>(
        _ path: String,
        method: HTTPMethod,
        body: Body?,
        query: [URLQueryItem],
        attempts: Int,
        idempotencyKey: String? = nil,
        extraHeaders: [String: String] = [:]
    ) async throws -> Response {
        guard var components = URLComponents(url: baseURL.appending(path: path), resolvingAgainstBaseURL: false) else {
            throw APIClientError.invalidConfiguration
        }
        components.queryItems = query.isEmpty ? nil : query
        guard let url = components.url else { throw APIClientError.invalidConfiguration }
        let scope = await auth.cacheScope()
        if !(await network.online()) {
            if method == .get,
               isDiskCacheAllowed(path),
               let cached = await cache.get(
                   key: cacheKey(url: url, scope: scope),
                   maxAge: cacheMaxAge(path)
               ),
               !isEmptyJSONArrayEnvelope(cached),
               let value = try? decoder.decode(APIEnvelope<Response>.self, from: cached).data {
                await diagnostics.record(requestID: "offline-cache", path: path)
                return value
            }
            throw APIClientError.offline
        }
        var finalError: Error = APIClientError.invalidResponse
        for attempt in 0..<attempts {
            try Task.checkCancellation()
            do {
                var request = URLRequest(url: url)
                request.cachePolicy = .reloadIgnoringLocalCacheData
                request.httpMethod = method.rawValue
                request.setValue("application/json", forHTTPHeaderField: "Accept")
                request.setValue(UUID().uuidString, forHTTPHeaderField: "X-Request-ID")
                for (name, value) in await auth.headers() { request.setValue(value, forHTTPHeaderField: name) }
                for (name, value) in extraHeaders {
                    request.setValue(value, forHTTPHeaderField: name)
                }
                if let idempotencyKey { request.setValue(idempotencyKey, forHTTPHeaderField: "Idempotency-Key") }
                if let body {
                    request.httpBody = try encoder.encode(body)
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                }
                let (data, response) = try await session.data(for: request)
                guard let http = response as? HTTPURLResponse else { throw APIClientError.invalidResponse }
                let requestID = http.value(forHTTPHeaderField: "X-Request-ID")
                await diagnostics.record(requestID: requestID, path: path)
                if http.statusCode == 401 {
                    await auth.markExpired()
                    await clearSessionData()
                    await MainActor.run { NotificationCenter.default.post(name: .oneMoreSessionExpired, object: nil) }
                    throw APIClientError.sessionExpired(requestID: requestID)
                }
                guard (200..<300).contains(http.statusCode) else {
                    let error = (try? decoder.decode(APIErrorEnvelope.self, from: data).error)
                        ?? APIErrorBody(code: "HTTP_\(http.statusCode)", message: "请求失败", details: [:], requestId: requestID)
                    throw APIClientError.server(status: http.statusCode, body: error)
                }
                do {
                    let value = try decoder.decode(APIEnvelope<Response>.self, from: data).data
                    if method == .get, isDiskCacheAllowed(path), !isEmptyJSONArrayEnvelope(data) {
                        await cache.put(data, key: cacheKey(url: url, scope: scope))
                    }
                    return value
                }
                catch { throw APIClientError.decoding(error.localizedDescription, requestID: requestID) }
            } catch is CancellationError {
                throw CancellationError()
            } catch let error as URLError where error.code == .cancelled {
                throw CancellationError()
            } catch let error as APIClientError {
                finalError = error
                if case .sessionExpired = error { throw error }
                if case .server = error { throw error }
                if case .decoding = error { throw error }
            } catch {
                if error.isCancellation { throw CancellationError() }
                if let urlError = error as? URLError,
                   [.notConnectedToInternet, .networkConnectionLost, .dataNotAllowed,
                    .internationalRoamingOff].contains(urlError.code) {
                    finalError = APIClientError.offline
                } else {
                    finalError = APIClientError.transport(error.localizedDescription)
                }
            }
            if attempt + 1 < attempts {
                try Task.checkCancellation()
                try await Task.sleep(for: .milliseconds(250 * (attempt + 1)))
            }
        }
        if method == .get, isDiskCacheAllowed(path),
           let cached = await cache.get(key: cacheKey(url: url, scope: scope), maxAge: cacheMaxAge(path)),
           !isEmptyJSONArrayEnvelope(cached),
           let value = try? decoder.decode(APIEnvelope<Response>.self, from: cached).data {
            await diagnostics.record(requestID: "offline-cache", path: path)
            return value
        }
        throw finalError
    }

    func authScope() async -> String { await auth.cacheScope() }

    func pendingMutations() async -> [PendingMutationJournal.Entry] {
        let scope = await auth.cacheScope()
        return await mutationJournal.entries(scope: scope)
    }

    /// Resumes durable idempotent writes only after asking the server whether
    /// the operation already exists. Unknown/in-progress outcomes remain
    /// visible as ambiguous and are never blindly executed a second time.
    func resumePendingMutations() async {
        guard await network.online() else { return }
        let scope = await auth.cacheScope()
        for entry in await mutationJournal.entries(scope: scope) {
            guard entry.state != .needsAttention else { continue }
            do {
                let status = try await operationStatus(entry)
                switch status {
                case "completed":
                    await mutationJournal.complete(entry.id)
                    continue
                case "in_progress", "unknown_after_interruption":
                    await mutationJournal.update(
                        entry.id,
                        state: .ambiguous,
                        errorCode: status
                    )
                    continue
                default:
                    break
                }
            } catch let error as APIClientError {
                if case let .server(status, _) = error, status == 404 {
                    // No reservation exists, so the exact saved operation is
                    // safe to submit once with its original key.
                    if entry.state == .ambiguous {
                        await mutationJournal.update(
                            entry.id,
                            state: .needsAttention,
                            errorCode: "AMBIGUOUS_RECORD_MISSING"
                        )
                        continue
                    }
                } else if case .offline = error {
                    return
                } else {
                    continue
                }
            } catch { continue }

            do {
                try await replay(entry)
                await mutationJournal.complete(entry.id)
            } catch let error as APIClientError {
                if case let .server(_, body) = error,
                   ["IDEMPOTENCY_IN_PROGRESS", "IDEMPOTENCY_RESULT_UNKNOWN"].contains(body.code) {
                    await mutationJournal.update(
                        entry.id,
                        state: .ambiguous,
                        errorCode: body.code
                    )
                } else if case .server = error {
                    await mutationJournal.update(
                        entry.id,
                        state: .needsAttention,
                        errorCode: "SERVER_REJECTED"
                    )
                }
            } catch { return }
        }
    }

    func clearSessionData() async {
        await cache.removeAll()
        imageCache.removeAllObjects()
        session.configuration.urlCache?.removeAllCachedResponses()
    }

    private func isDiskCacheAllowed(_ path: String) -> Bool {
        path == "/competitions" || path.hasPrefix("/competitions/")
            || path == "/events" || path.hasPrefix("/events/")
            || path == "/today/summary"
            || path == "/gatherings/mine" || path == "/gatherings/open"
            || path.hasPrefix("/gatherings/") && !path.hasSuffix("/action-capability")
            || path == "/relations" || path.hasPrefix("/relations/")
            || path == "/notifications" || path == "/trust/me"
            || path == "/me/notification-preferences" || path == "/me/privacy"
    }

    private func cacheMaxAge(_ path: String) -> TimeInterval {
        path.hasPrefix("/competitions") || path.hasPrefix("/events") ? 15 * 60 : 5 * 60
    }

    /// 空列表不落盘：灌库前的 `[]` 不能把之后的真实目录挡住。
    private func isEmptyJSONArrayEnvelope(_ data: Data) -> Bool {
        guard let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let arr = obj["data"] as? [Any] else { return false }
        return arr.isEmpty
    }

    private func cacheKey(url: URL, scope: String) -> String { "\(scope)|\(url.absoluteString)" }

    private struct OperationStatus: Decodable, Sendable { let status: String }

    private func operationStatus(_ entry: PendingMutationJournal.Entry) async throws -> String {
        let query = [
            URLQueryItem(name: "method", value: entry.method),
            URLQueryItem(name: "path", value: entry.path),
        ]
        let value: OperationStatus = try await request(
            "/idempotency/operations/\(entry.idempotencyKey)",
            method: .get,
            body: Optional<EmptyRequest>.none,
            query: query,
            attempts: 1
        )
        return value.status
    }

    private func replay(_ entry: PendingMutationJournal.Entry) async throws {
        guard let method = HTTPMethod(rawValue: entry.method) else {
            await mutationJournal.update(entry.id, state: .needsAttention, errorCode: "INVALID_METHOD")
            throw APIClientError.invalidConfiguration
        }
        let url = baseURL.appending(path: entry.path)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = entry.body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(entry.idempotencyKey, forHTTPHeaderField: "Idempotency-Key")
        request.setValue(UUID().uuidString, forHTTPHeaderField: "X-Request-ID")
        for (name, value) in await auth.headers() { request.setValue(value, forHTTPHeaderField: name) }
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw APIClientError.invalidResponse }
        if http.statusCode == 401 { throw APIClientError.sessionExpired(requestID: nil) }
        guard (200..<300).contains(http.statusCode) else {
            let body = (try? decoder.decode(APIErrorEnvelope.self, from: data).error)
                ?? APIErrorBody(code: "HTTP_\(http.statusCode)", message: "恢复写操作失败", details: [:], requestId: nil)
            throw APIClientError.server(status: http.statusCode, body: body)
        }
    }
}

extension Notification.Name {
    static let oneMoreSessionExpired = Notification.Name("OneMoreSessionExpired")
    static let oneMoreSocialPreferencesDidChange = Notification.Name("OneMoreSocialPreferencesDidChange")
}

extension JSONDecoder {
    static var oneMore: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        decoder.dateDecodingStrategy = .custom { decoder in
            let value = try decoder.singleValueContainer().decode(String.self)
            if let date = ISO8601DateFormatter.fractional.date(from: value) ?? ISO8601DateFormatter.standard.date(from: value) { return date }
            throw DecodingError.dataCorruptedError(in: try decoder.singleValueContainer(), debugDescription: "Invalid RFC3339 date: \(value)")
        }
        return decoder
    }
}

extension JSONEncoder {
    static var oneMore: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        encoder.dateEncodingStrategy = .iso8601
        encoder.outputFormatting = [.sortedKeys]
        return encoder
    }
}

extension ISO8601DateFormatter {
    fileprivate static let standard = ISO8601DateFormatter()
    fileprivate static let fractional: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()
}
