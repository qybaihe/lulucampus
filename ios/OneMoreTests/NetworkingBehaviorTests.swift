import Foundation
import XCTest
@testable import ONE_MORE

final class StubURLProtocol: URLProtocol {
    static let lock = NSLock()
    static var handler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }
    override func startLoading() {
        do {
            Self.lock.lock(); let handler = Self.handler; Self.lock.unlock()
            guard let handler else { throw URLError(.badServerResponse) }
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }
    override func stopLoading() {}
}

final class NetworkingBehaviorTests: XCTestCase {
    private struct Probe: Codable, Sendable, Equatable { let value: String }
    private struct Body: Codable, Sendable { let value: String }

    override func tearDown() {
        StubURLProtocol.lock.lock(); StubURLProtocol.handler = nil; StubURLProtocol.lock.unlock()
        super.tearDown()
    }

    private func makeClient() -> (APIClient, AuthManager, NetworkDiagnostics) {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        let diagnostics = NetworkDiagnostics()
        let auth = AuthManager(keychain: .init(service: "tests.network.\(UUID().uuidString)"))
        let cache = ResponseCache(root: FileManager.default.temporaryDirectory.appending(path: UUID().uuidString))
        let journal = IdempotencyKeyJournal(keychain: .init(service: "tests.idempotency.\(UUID().uuidString)"))
        return (APIClient(baseURL: URL(string: "https://unit.test")!, auth: auth, diagnostics: diagnostics, session: URLSession(configuration: configuration), cache: cache, idempotencyJournal: journal), auth, diagnostics)
    }

    private func response(_ request: URLRequest, status: Int = 200, requestID: String = "req-unit") -> HTTPURLResponse {
        HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: ["X-Request-ID": requestID])!
    }

    private func requestBody(_ request: URLRequest) -> Data {
        if let body = request.httpBody { return body }
        guard let stream = request.httpBodyStream else { return Data() }
        stream.open()
        defer { stream.close() }
        var data = Data()
        var buffer = [UInt8](repeating: 0, count: 1_024)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            guard count > 0 else { break }
            data.append(buffer, count: count)
        }
        return data
    }

    func testSuccessEnvelopeRecordsRequestIDAndDevAuth() async throws {
        let (client, _, diagnostics) = makeClient()
        StubURLProtocol.handler = { request in
            #if DEV_AUTH
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-User-ID"), "u_demo_1")
            #endif
            return (self.response(request), Data(#"{"data":{"value":"live"},"meta":{}}"#.utf8))
        }
        let value: Probe = try await client.get("/probe")
        XCTAssertEqual(value, Probe(value: "live"))
        let snapshot = await diagnostics.snapshot()
        XCTAssertEqual(snapshot.0, "req-unit")
        XCTAssertEqual(snapshot.1, "/probe")
    }

    func testTastePhoneCodeUsesDedicatedEndpointsAndSnakeCaseWithoutPersistingRawPhone() async throws {
        let (client, _, _) = makeClient()
        let repository = TasteImportRepository(api: client)
        var calls = 0
        StubURLProtocol.handler = { request in
            calls += 1
            XCTAssertEqual(request.url?.path, "/profile/imports/taste-1/phone/code")
            XCTAssertEqual(request.httpMethod, "POST")
            let body = try XCTUnwrap(
                try JSONSerialization.jsonObject(with: self.requestBody(request)) as? [String: String]
            )
            XCTAssertEqual(body, ["phone": "13800138000", "country_code": "86"])
            let response = #"{"data":{"import_id":"taste-1","status":"WAITING_SMS_CODE","phone_masked":"138****8000","code_sent":true,"verified":false,"authenticated_at":null,"submit_code":"/profile/imports/taste-1/phone/verify","verify":"/profile/imports/taste-1/verify","error":null},"meta":{}}"#
            return (self.response(request), Data(response.utf8))
        }
        let result = try await repository.requestPhoneCode(
            "taste-1", phone: "13800138000", countryCode: "86"
        )
        XCTAssertEqual(calls, 1)
        XCTAssertEqual(result.phoneMasked, "138****8000")
    }

    @MainActor
    func testFirstUseCanFinishWithSocialExplicitlyOff() async throws {
        let (client, _, _) = makeClient()
        StubURLProtocol.handler = { request in
            XCTAssertEqual(request.url?.path, "/me/privacy")
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(
                request.value(forHTTPHeaderField: "Idempotency-Key"),
                "first-use-social-off"
            )
            let body = String(decoding: self.requestBody(request), as: UTF8.self)
            XCTAssertTrue(body.contains(#""social_enabled":false"#))
            return (
                self.response(request),
                Data(#"{"data":{"social_enabled":false,"course_matching_enabled":false,"identity_disclosure":"after_confirmed","same_gender_only":false,"minimum_group_size":3,"scene_sensitive_policy":"mute_onsite"},"meta":{}}"#.utf8)
            )
        }
        let model = FirstUseSetupViewModel(repository: IdentityRepository(api: client))
        model.step = .social
        await model.keepSocialOff()
        if case .ready = model.step {} else { XCTFail("Skip must reach ready") }
        XCTAssertNil(model.error)
    }

    func testServerErrorEnvelopePreservesCodeDetailsAndRequestID() async {
        let (client, _, _) = makeClient()
        StubURLProtocol.handler = { request in
            let body = #"{"error":{"code":"STALE_PREVIEW","message":"预览已过期","details":{"action_id":"a1"},"request_id":"req-error"}}"#
            return (self.response(request, status: 409, requestID: "req-error"), Data(body.utf8))
        }
        do {
            let _: Probe = try await client.get("/probe")
            XCTFail("Expected server error")
        } catch let APIClientError.server(status, body) {
            XCTAssertEqual(status, 409)
            XCTAssertEqual(body.code, "STALE_PREVIEW")
            XCTAssertEqual(body.requestId, "req-error")
            XCTAssertEqual(body.details["action_id"], .string("a1"))
        } catch { XCTFail("Unexpected error: \(error)") }
    }

    func test401MarksSessionExpiredAndBroadcastsRecoverySignal() async {
        let (client, auth, _) = makeClient()
        let notification = expectation(forNotification: .oneMoreSessionExpired, object: nil)
        StubURLProtocol.handler = { request in
            let body = #"{"error":{"code":"SESSION_EXPIRED","message":"expired","details":{},"request_id":"req-401"}}"#
            return (self.response(request, status: 401, requestID: "req-401"), Data(body.utf8))
        }
        do {
            let _: Probe = try await client.get("/private")
            XCTFail("Expected session expiration")
        } catch let APIClientError.sessionExpired(requestID) {
            XCTAssertEqual(requestID, "req-401")
        } catch { XCTFail("Unexpected error: \(error)") }
        await fulfillment(of: [notification], timeout: 1)
        let state = await auth.state
        XCTAssertEqual(state, .expired)
    }

    func testGETRetriesTransportThenUsesFreshOfflineCache() async throws {
        let (client, _, diagnostics) = makeClient()
        var callCount = 0
        StubURLProtocol.handler = { request in
            callCount += 1
            return (self.response(request), Data(#"{"data":{"value":"cached-live"},"meta":{}}"#.utf8))
        }
        let first: Probe = try await client.get("/competitions/cached")
        XCTAssertEqual(first.value, "cached-live")
        StubURLProtocol.handler = { _ in callCount += 1; throw URLError(.notConnectedToInternet) }
        let cached: Probe = try await client.get("/competitions/cached")
        XCTAssertEqual(cached.value, "cached-live")
        XCTAssertEqual(callCount, 3, "one success plus two read retries")
        let snapshot = await diagnostics.snapshot()
        XCTAssertEqual(snapshot.0, "offline-cache")
    }

    func testWriteWithoutIdempotencyDoesNotRetry() async {
        let (client, _, _) = makeClient()
        var calls = 0
        StubURLProtocol.handler = { _ in calls += 1; throw URLError(.timedOut) }
        do {
            let _: Probe = try await client.send("/write", method: .post, body: Body(value: "one"))
            XCTFail("Expected timeout")
        } catch { XCTAssertEqual(calls, 1) }
    }

    func testIdempotentWriteRetriesWithSameKey() async throws {
        let (client, _, _) = makeClient()
        var calls = 0
        StubURLProtocol.handler = { request in
            calls += 1
            XCTAssertEqual(request.value(forHTTPHeaderField: "Idempotency-Key"), "idem-1")
            if calls == 1 { throw URLError(.networkConnectionLost) }
            return (self.response(request), Data(#"{"data":{"value":"once"},"meta":{}}"#.utf8))
        }
        let value: Probe = try await client.send("/write", method: .post, body: Body(value: "one"), idempotencyKey: "idem-1")
        XCTAssertEqual(value.value, "once")
        XCTAssertEqual(calls, 2)
    }

    func testManualRetryAfterTwoLostResponsesKeepsLogicalOperationKey() async throws {
        let (client, _, _) = makeClient()
        var observed: [String] = []
        StubURLProtocol.handler = { request in
            observed.append(request.value(forHTTPHeaderField: "Idempotency-Key") ?? "missing")
            throw URLError(.networkConnectionLost)
        }
        do {
            let _: Probe = try await client.send(
                "/write", method: .post, body: Body(value: "same-logical-operation"),
                idempotencyKey: "first-generated-key"
            )
            XCTFail("Expected lost response")
        } catch {}
        StubURLProtocol.handler = { request in
            observed.append(request.value(forHTTPHeaderField: "Idempotency-Key") ?? "missing")
            return (self.response(request), Data(#"{"data":{"value":"replayed"},"meta":{}}"#.utf8))
        }
        let value: Probe = try await client.send(
            "/write", method: .post, body: Body(value: "same-logical-operation"),
            idempotencyKey: "new-key-from-view-retry"
        )
        XCTAssertEqual(value.value, "replayed")
        XCTAssertEqual(observed, ["first-generated-key", "first-generated-key", "first-generated-key"])
    }

    func testOfflineIdempotentWritePersistsThenResumesAfterServerStatusCheck() async throws {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        let auth = AuthManager(keychain: .init(service: "tests.offline.auth.\(UUID().uuidString)"))
        let availability = NetworkAvailability(initiallyOnline: false)
        let mutationJournal = PendingMutationJournal(
            keychain: .init(service: "tests.offline.journal.\(UUID().uuidString)")
        )
        let client = APIClient(
            baseURL: URL(string: "https://unit.test")!,
            auth: auth,
            session: URLSession(configuration: configuration),
            cache: ResponseCache(root: FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)),
            idempotencyJournal: IdempotencyKeyJournal(
                keychain: .init(service: "tests.offline.keys.\(UUID().uuidString)")
            ),
            mutationJournal: mutationJournal,
            network: availability
        )
        var calls = 0
        StubURLProtocol.handler = { _ in
            calls += 1
            throw URLError(.badServerResponse)
        }
        do {
            let _: Probe = try await client.send(
                "/gatherings/g1/confirm",
                method: .post,
                body: Body(value: "confirm"),
                idempotencyKey: "offline-confirm-key"
            )
            XCTFail("Expected explicit offline state")
        } catch APIClientError.offline {}
        XCTAssertEqual(calls, 0, "known-offline writes must fail fast without opening a socket")
        var pending = await client.pendingMutations()
        XCTAssertEqual(pending.count, 1)
        XCTAssertEqual(pending.first?.state, .pending)

        await availability.update(true)
        var paths: [String] = []
        StubURLProtocol.handler = { request in
            paths.append(request.url!.path)
            if request.url!.path.hasPrefix("/idempotency/operations/") {
                let body = #"{"error":{"code":"NOT_FOUND","message":"not found","details":{},"request_id":"status-404"}}"#
                return (self.response(request, status: 404), Data(body.utf8))
            }
            XCTAssertEqual(request.value(forHTTPHeaderField: "Idempotency-Key"), "offline-confirm-key")
            return (self.response(request), Data(#"{"data":{"value":"resumed"},"meta":{}}"#.utf8))
        }
        await client.resumePendingMutations()
        pending = await client.pendingMutations()
        XCTAssertTrue(pending.isEmpty)
        XCTAssertEqual(paths.count, 2)
        XCTAssertTrue(paths[0].hasPrefix("/idempotency/operations/"))
        XCTAssertEqual(paths[1], "/gatherings/g1/confirm")
    }

    func testDecodingErrorDoesNotRetryAndKeepsRequestID() async {
        let (client, _, _) = makeClient()
        var calls = 0
        StubURLProtocol.handler = { request in calls += 1; return (self.response(request, requestID: "req-decode"), Data(#"{"data":{"wrong":1},"meta":{}}"#.utf8)) }
        do {
            let _: Probe = try await client.get("/bad-shape")
            XCTFail("Expected decoding error")
        } catch let APIClientError.decoding(_, requestID) {
            XCTAssertEqual(requestID, "req-decode")
            XCTAssertEqual(calls, 1)
        } catch { XCTFail("Unexpected error: \(error)") }
    }

    func testAuthenticatedImageUsesHeaderBoundMemoryCacheAndSessionClear() async throws {
        let (client, auth, _) = makeClient()
        var calls = 0
        let png = Data([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 1, 2, 3])
        StubURLProtocol.handler = { request in
            calls += 1
            #if DEV_AUTH
            XCTAssertEqual(request.value(forHTTPHeaderField: "X-User-ID"), "u_demo_1")
            #endif
            XCTAssertEqual(request.cachePolicy, .reloadIgnoringLocalCacheData)
            return (
                HTTPURLResponse(
                    url: request.url!, statusCode: 200, httpVersion: "HTTP/1.1",
                    headerFields: ["Content-Type": "image/png", "X-Request-ID": "image-request"]
                )!,
                png
            )
        }
        let first = try await client.authenticatedImage("/media/images/m1")
        let second = try await client.authenticatedImage("/media/images/m1")
        XCTAssertEqual(first, png)
        XCTAssertEqual(second, png)
        XCTAssertEqual(calls, 1)
        await client.clearSessionData()
        let afterClear = try await client.authenticatedImage("/media/images/m1")
        XCTAssertEqual(afterClear, png)
        XCTAssertEqual(calls, 2)
        await auth.clear()
    }
}
