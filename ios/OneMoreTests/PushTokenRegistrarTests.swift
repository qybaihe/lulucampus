import Foundation
import XCTest
@testable import ONE_MORE

final class PushTokenRegistrarTests: XCTestCase {
    private final class OperationLog: @unchecked Sendable {
        private let lock = NSLock()
        private var values: [String] = []

        func append(_ value: String) {
            lock.lock(); defer { lock.unlock() }
            values.append(value)
        }

        func snapshot() -> [String] {
            lock.lock(); defer { lock.unlock() }
            return values
        }
    }

    override func tearDown() {
        StubURLProtocol.lock.lock()
        StubURLProtocol.handler = nil
        StubURLProtocol.lock.unlock()
        super.tearDown()
    }

    private func requestBody(_ request: URLRequest) -> Data {
        if let body = request.httpBody { return body }
        guard let stream = request.httpBodyStream else { return Data() }
        stream.open()
        defer { stream.close() }
        var result = Data()
        var buffer = [UInt8](repeating: 0, count: 1_024)
        while stream.hasBytesAvailable {
            let count = stream.read(&buffer, maxLength: buffer.count)
            guard count > 0 else { break }
            result.append(buffer, count: count)
        }
        return result
    }

    private func makeAPI(auth: AuthManager) -> APIClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        return APIClient(
            baseURL: URL(string: "https://push.test")!,
            auth: auth,
            session: URLSession(configuration: configuration),
            cache: ResponseCache(root: FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)),
            idempotencyJournal: IdempotencyKeyJournal(keychain: .init(service: "tests.push.idempotency.\(UUID().uuidString)"))
        )
    }

    @MainActor
    private func waitForRegistered(_ registrar: PushTokenRegistrar) async {
        for _ in 0..<100 {
            if registrar.status == .registered { return }
            try? await Task.sleep(for: .milliseconds(20))
        }
        XCTFail("push registrar did not reach registered")
    }

    @MainActor
    private func waitForOperations(_ count: Int, in log: OperationLog) async {
        for _ in 0..<150 {
            if log.snapshot().count >= count { return }
            try? await Task.sleep(for: .milliseconds(20))
        }
        XCTFail("push registrar did not finish \(count) network operations")
    }

    @MainActor
    func testTokenRotationRevokesAtomicOldPairBeforeRegisteringNewToken() async {
        let auth = AuthManager(keychain: .init(service: "tests.push.auth.\(UUID().uuidString)"))
        let api = makeAPI(auth: auth)
        let registrar = PushTokenRegistrar(
            api: api,
            auth: auth,
            keychain: .init(service: "tests.push.state.\(UUID().uuidString)")
        )
        let operations = OperationLog()
        StubURLProtocol.handler = { request in
            let rawBody = self.requestBody(request)
            let body = (try? JSONSerialization.jsonObject(with: rawBody) as? [String: Any]) ?? [:]
            let token = body["token"] as? String ?? ""
            if request.httpMethod == "DELETE" {
                operations.append("delete:\(token)")
                let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: [:])!
                return (response, Data(#"{"data":{"active":false,"deactivated":1},"meta":{}}"#.utf8))
            }
            operations.append("register:\(token)")
            let response = HTTPURLResponse(url: request.url!, statusCode: 201, httpVersion: nil, headerFields: [:])!
            let payload = #"{"data":{"id":"d1","active":true,"deactivation_token":"proof-abcdefghijklmnopqrstuvwxyz-#(token)"},"meta":{}}"#
            return (response, Data(payload.utf8))
        }
        let first = Data(repeating: 0x11, count: 32)
        let second = Data(repeating: 0x22, count: 32)
        let firstHex = first.map { String(format: "%02x", $0) }.joined()
        let secondHex = second.map { String(format: "%02x", $0) }.joined()
        registrar.receive(deviceToken: first)
        await waitForOperations(1, in: operations)
        await waitForRegistered(registrar)
        registrar.receive(deviceToken: second)
        await waitForOperations(3, in: operations)
        await waitForRegistered(registrar)
        XCTAssertEqual(operations.snapshot(), ["register:\(firstHex)", "delete:\(firstHex)", "register:\(secondHex)"])
    }

    @MainActor
    func testExpiryCleanupCompletesBeforeFastReauthenticationRegistersAgain() async {
        let auth = AuthManager(keychain: .init(service: "tests.push.fast-auth.\(UUID().uuidString)"))
        let api = makeAPI(auth: auth)
        let registrar = PushTokenRegistrar(
            api: api,
            auth: auth,
            keychain: .init(service: "tests.push.fast-state.\(UUID().uuidString)")
        )
        let operations = OperationLog()
        StubURLProtocol.handler = { request in
            if request.httpMethod == "DELETE" {
                operations.append("delete-old")
                Thread.sleep(forTimeInterval: 0.08)
                return (
                    HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: [:])!,
                    Data(#"{"data":{"active":false,"deactivated":1},"meta":{}}"#.utf8)
                )
            }
            operations.append("register")
            return (
                HTTPURLResponse(url: request.url!, statusCode: 201, httpVersion: nil, headerFields: [:])!,
                Data(#"{"data":{"id":"d1","active":true,"deactivation_token":"proof-abcdefghijklmnopqrstuvwxyz-fast"},"meta":{}}"#.utf8)
            )
        }
        let session = AppSessionController(
            auth: auth,
            deactivateNotificationsBeforeSignOut: { try await registrar.deactivateBeforeSignOut() },
            deactivateNotificationsAfterExpiry: { await registrar.deactivateAfterSessionExpiry() },
            resumeNotificationsAfterAuthentication: { await registrar.resumeAfterAuthentication() }
        )
        registrar.receive(deviceToken: Data(repeating: 0x33, count: 32))
        await waitForOperations(1, in: operations)
        await waitForRegistered(registrar)
        session.expire()
        await session.install(token: "e30.eyJzdWIiOiJ1X2RlbW9fMiJ9.signature", needsOnboarding: false)
        await waitForOperations(3, in: operations)
        await waitForRegistered(registrar)
        XCTAssertEqual(operations.snapshot(), ["register", "delete-old", "register"])
    }
}
