import Foundation
import XCTest
@testable import ONE_MORE

final class ViewModelBehaviorTests: XCTestCase {
    private func client() -> APIClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubURLProtocol.self]
        let auth = AuthManager(keychain: .init(service: "tests.viewmodel.\(UUID().uuidString)"))
        return APIClient(
            baseURL: URL(string: "https://viewmodel.test")!,
            auth: auth,
            session: URLSession(configuration: configuration),
            cache: ResponseCache(root: FileManager.default.temporaryDirectory.appending(path: UUID().uuidString)),
            idempotencyJournal: IdempotencyKeyJournal(
                keychain: .init(service: "tests.viewmodel.idempotency.\(UUID().uuidString)")
            )
        )
    }

    override func tearDown() {
        StubURLProtocol.lock.lock()
        StubURLProtocol.handler = nil
        StubURLProtocol.lock.unlock()
        super.tearDown()
    }

    private func response(_ request: URLRequest, status: Int = 200) -> HTTPURLResponse {
        HTTPURLResponse(url: request.url!, statusCode: status, httpVersion: "HTTP/1.1", headerFields: ["X-Request-ID": "vm-request"])!
    }

    @MainActor
    func testChannelViewModelSuppressesDuplicateTap() async {
        let api = client()
        let social = SocialRepository(api: api)
        let socket = WebSocketClient(baseURL: URL(string: "wss://viewmodel.test")!, auth: AuthManager(keychain: .init(service: "tests.socket.\(UUID().uuidString)")))
        let model = ChannelViewModel(channelID: "c1", social: social, socket: socket)
        model.draft = "只发送一次"
        var calls = 0
        let requestEntered = expectation(description: "first send entered URL loading")
        let allowResponse = DispatchSemaphore(value: 0)
        StubURLProtocol.handler = { request in
            calls += 1
            requestEntered.fulfill()
            XCTAssertEqual(allowResponse.wait(timeout: .now() + 2), .success)
            let body = #"{"data":{"id":"m1","channel_id":"c1","sender_id":"u_demo_1","sender_type":"human","content_type":"text","content":"只发送一次","image":null,"location":null,"sent_at":"2026-08-11T15:00:00Z"},"meta":{}}"#
            return (self.response(request), Data(body.utf8))
        }
        let firstTask = Task { await model.send() }
        await fulfillment(of: [requestEntered], timeout: 2)
        XCTAssertTrue(model.sending)
        let duplicate = await model.send()
        allowResponse.signal()
        let accepted = await firstTask.value
        XCTAssertTrue(accepted)
        XCTAssertFalse(duplicate)
        XCTAssertEqual(calls, 1)
        XCTAssertEqual(model.messages.map(\.id), ["m1"])
    }

    @MainActor
    func testChannelViewModelRecoversAfterErrorAndClearsMessage() async {
        let api = client()
        let social = SocialRepository(api: api)
        let socket = WebSocketClient(baseURL: URL(string: "wss://viewmodel.test")!, auth: AuthManager(keychain: .init(service: "tests.socket.\(UUID().uuidString)")))
        let model = ChannelViewModel(channelID: "c1", social: social, socket: socket)
        model.draft = "第一次"
        StubURLProtocol.handler = { request in
            let body = #"{"error":{"code":"TEMPORARY","message":"稍后重试","details":{},"request_id":"vm-request"}}"#
            return (self.response(request, status: 503), Data(body.utf8))
        }
        let firstAttempt = await model.send()
        XCTAssertFalse(firstAttempt)
        XCTAssertNotNil(model.error)

        model.draft = "第二次"
        StubURLProtocol.handler = { request in
            let body = #"{"data":{"id":"m2","channel_id":"c1","sender_id":"u_demo_1","sender_type":"human","content_type":"text","content":"第二次","image":null,"location":null,"sent_at":"2026-08-11T15:01:00Z"},"meta":{}}"#
            return (self.response(request), Data(body.utf8))
        }
        let secondAttempt = await model.send()
        XCTAssertTrue(secondAttempt)
        XCTAssertNil(model.error)
        XCTAssertEqual(model.messages.last?.id, "m2")
    }

    @MainActor
    func testGatheringListRetryTransitionsFromFailureToEmpty() async {
        let repository = GatheringRepository(api: client())
        let model = GatheringListViewModel(mine: true, repository: repository)
        StubURLProtocol.handler = { request in
            let body = #"{"error":{"code":"TEMPORARY","message":"网络错误","details":{},"request_id":"vm-request"}}"#
            return (self.response(request, status: 503), Data(body.utf8))
        }
        await model.load()
        if case .failed = model.phase {} else { XCTFail("Expected failure") }

        StubURLProtocol.handler = { request in (self.response(request), Data(#"{"data":[],"meta":{}}"#.utf8)) }
        await model.load()
        if case let .loaded(items) = model.phase { XCTAssertTrue(items.isEmpty) }
        else { XCTFail("Expected loaded empty state") }
    }

    @MainActor
    func testIntentPublishCommitThenLostResponseRecoversBeforeAnyDuplicate() async {
        let repository = IntentRepository(api: client())
        let model = IntentComposerViewModel(repository: repository)
        let start = Date(timeIntervalSince1970: 1_788_825_600)
        let card = IntentCard(
            id: "card-fixture",
            status: "Draft",
            gatheringType: "sports",
            mode: "single",
            goal: "周六打羽毛球",
            capabilities: [.init(key: "badminton", source: "self_reported")],
            requiredRoles: [],
            intensity: "认真参与",
            availableWindows: [.init(startAt: start, endAt: start.addingTimeInterval(7_200), stability: 1)],
            campus: "珠海校区",
            minSize: 3,
            targetSize: 4,
            socialMode: "reveal_after_full",
            competitionId: nil,
            expiresAt: start.addingTimeInterval(86_400),
            fieldSources: [:],
            clarificationRounds: 0
        )
        model.prepare(card)
        var publishCalls = 0
        var publicationCalls = 0
        StubURLProtocol.handler = { request in
            switch (request.httpMethod, request.url?.path) {
            case ("PATCH", "/intent/card-fixture"):
                let data = Data("{\"data\":".utf8)
                    + (try JSONEncoder.oneMore.encode(card))
                    + Data(",\"meta\":{}}".utf8)
                return (self.response(request), data)
            case ("POST", "/intent/publish"):
                publishCalls += 1
                throw URLError(.networkConnectionLost)
            case ("GET", "/intent/card-fixture/publication"):
                publicationCalls += 1
                let result = IntentPublishResult(
                    intentId: card.id,
                    gatheringId: "gathering-committed-once",
                    status: "Pooling",
                    expiresAt: card.expiresAt
                )
                let data = Data("{\"data\":".utf8)
                    + (try JSONEncoder.oneMore.encode(result))
                    + Data(",\"meta\":{}}".utf8)
                return (self.response(request), data)
            default:
                throw URLError(.badURL)
            }
        }

        let recovered = await model.publish(card)
        XCTAssertTrue(recovered)
        XCTAssertEqual(publishCalls, 2, "transport retry must reuse the same journal key")
        XCTAssertEqual(publicationCalls, 1)
        XCTAssertNil(model.pendingPublishKey)
        if case let .published(result) = model.phase {
            XCTAssertEqual(result.gatheringId, "gathering-committed-once")
        } else {
            XCTFail("Expected server publication recovery")
        }
    }
}
