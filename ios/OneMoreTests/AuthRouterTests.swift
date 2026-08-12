import XCTest
@testable import ONE_MORE

final class AuthRouterTests: XCTestCase {
    func testBrandArchitectureAndBundleDisplayNamesStayConsistent() throws {
        XCTAssertEqual(AppBrand.displayName, "噜噜成局")
        XCTAssertEqual(AppBrand.mascotName, "噜噜")
        XCTAssertEqual(AppBrand.coreAction, "差一个")
        XCTAssertEqual(AppBrand.slogan, "差一个，就成局")
        XCTAssertEqual(RootTab.create.title, AppBrand.coreAction)

        let iosRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        for name in ["Info-Debug.plist", "Info-Release.plist"] {
            let data = try Data(contentsOf: iosRoot.appendingPathComponent("Config/\(name)"))
            let plist = try XCTUnwrap(
                PropertyListSerialization.propertyList(from: data, format: nil) as? [String: Any]
            )
            XCTAssertEqual(plist["CFBundleDisplayName"] as? String, AppBrand.displayName, name)
        }
    }

    func testAllSeventyFourFormalNodesHaveConcreteProductionTriggers() {
        let definitions = FormalNodeRegistry.all
        XCTAssertEqual(definitions.count, 74)
        XCTAssertEqual(Set(definitions.map(\.id)), Set(FormalNodeID.allCases))
        XCTAssertEqual(Set(definitions.map(\.accessibilityIdentifier)).count >= 60, true)
        for definition in definitions {
            XCTAssertFalse(definition.trigger.component.contains("Generic"), definition.id.rawValue)
            XCTAssertFalse(definition.trigger.component.contains("ContextRequired"), definition.id.rawValue)
            XCTAssertFalse(definition.accessibilityIdentifier.isEmpty, definition.id.rawValue)
            switch definition.trigger {
            case let .route(path, component):
                XCTAssertTrue(path.hasPrefix("/"), definition.id.rawValue)
                XCTAssertFalse(component.isEmpty)
            case let .serverState(endpoint, predicate, component):
                XCTAssertTrue(endpoint.hasPrefix("/"), definition.id.rawValue)
                XCTAssertFalse(predicate.isEmpty)
                XCTAssertFalse(component.isEmpty)
            case let .systemEvent(event, component):
                XCTAssertFalse(event.isEmpty)
                XCTAssertFalse(component.isEmpty)
            case let .app(component):
                XCTAssertFalse(component.isEmpty)
            }
        }
        XCTAssertEqual(FormalNodeRegistry.extraCompositeIDs, ["B12.2", "MSG"])
    }

    func testEveryServerStateEndpointMatchesFrozenOpenAPI() throws {
        let workspaceRoot = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let openAPIURL = workspaceRoot.appendingPathComponent("openapi/onemore.openapi.json")
        let data = try Data(contentsOf: openAPIURL)
        let document = try XCTUnwrap(
            JSONSerialization.jsonObject(with: data) as? [String: Any],
            "Frozen OpenAPI document is not a JSON object"
        )
        let paths = try XCTUnwrap(
            document["paths"] as? [String: Any],
            "Frozen OpenAPI document has no paths object"
        )
        let exactPaths = Set(paths.keys)
        let normalize: (String) -> String = {
            $0.replacingOccurrences(
                of: #"\{[^/]+\}"#,
                with: "{}",
                options: .regularExpression
            )
        }
        let normalizedPaths = Set(exactPaths.map(normalize))

        for definition in FormalNodeRegistry.all {
            guard case let .serverState(endpoint, _, _) = definition.trigger else { continue }
            XCTAssertTrue(
                normalizedPaths.contains(normalize(endpoint)),
                "\(definition.id.rawValue) endpoint is absent from generated OpenAPI: \(endpoint)"
            )
            XCTAssertTrue(
                exactPaths.contains(endpoint),
                "\(definition.id.rawValue) must use the exact generated OpenAPI placeholder names: \(endpoint)"
            )
        }
    }

    func testScreenDeepLinksResolveToTypedFormalNodeRoutes() {
        XCTAssertEqual(
            AppRoute.parse(URL(string: "onemore://screen/B5")!),
            .formal(.b5)
        )
        XCTAssertEqual(
            AppRoute.parse(URL(string: "onemore://screen/E11")!),
            .formal(.e11)
        )
    }

    @MainActor func testColdStartNotificationAndCalendarEventsDrainAfterRootInstallsHandlers() {
        OneMoreAppDelegate.resetDeliveryStateForTests()
        let url = URL(string: "onemore://action/action-cold-start")!
        OneMoreAppDelegate.receiveNotificationURL(url)
        OneMoreAppDelegate.receiveCalendarEvent(.refresh(gatheringID: "g-cold-start"))
        OneMoreAppDelegate.receiveToken(Data([0x01, 0x02]))

        var deliveredURLs: [URL] = []
        var deliveredEvents: [CalendarPushEvent] = []
        var deliveredTokens: [Data] = []
        OneMoreAppDelegate.installDeliveryHandlers(
            token: { deliveredTokens.append($0) },
            notificationURL: { deliveredURLs.append($0) },
            calendar: { deliveredEvents.append($0) }
        )
        XCTAssertEqual(deliveredURLs, [url])
        XCTAssertEqual(deliveredEvents, [.refresh(gatheringID: "g-cold-start")])
        XCTAssertEqual(deliveredTokens, [Data([0x01, 0x02])])
        OneMoreAppDelegate.resetDeliveryStateForTests()
    }

    func testDebugAuthHeaderAndTokenLifecycle() async {
        let store = KeychainStore(service: "tests.\(UUID().uuidString)")
        let auth = AuthManager(keychain: store)
        await auth.clear()
        #if DEV_AUTH
        let devHeaders = await auth.headers()
        XCTAssertNil(devHeaders["X-User-ID"])
        #endif
        await auth.install(token: "TOKEN")
        let tokenHeaders = await auth.headers()
        XCTAssertEqual(tokenHeaders["Authorization"], "Bearer TOKEN")
        await auth.markExpired()
        let state = await auth.state
        XCTAssertEqual(state, .expired)
        await auth.clear()
    }

    func testBearerSubjectDrivesCurrentUserWithoutReleaseFixtureID() async {
        let auth = AuthManager(keychain: .init(service: "tests.identity.\(UUID().uuidString)"))
        await auth.clear()
        await auth.install(token: "e30.eyJzdWIiOiJ1X3Byb2R1Y3Rpb25fNDIifQ.signature")
        let current = await auth.currentUserID()
        XCTAssertEqual(current, "u_production_42")
        await auth.clear()
    }

    func testExpiredCredentialCannotReauthenticateAfterProcessRestart() async {
        let store = KeychainStore(service: "tests.expired-restart.\(UUID().uuidString)")
        let first = AuthManager(keychain: store)
        await first.install(token: "e30.eyJzdWIiOiJ1X2RlbW9fMSJ9.signature")
        await first.markExpired()
        let restarted = AuthManager(keychain: store)
        let expiredState = await restarted.state
        let expiredHeaders = await restarted.headers()
        XCTAssertEqual(expiredState, .expired)
        XCTAssertTrue(expiredHeaders.isEmpty)
        await restarted.install(token: "e30.eyJzdWIiOiJ1X2RlbW9fMSJ9.new")
        let installedState = await restarted.state
        XCTAssertEqual(installedState, .authenticated)
        await restarted.clear()
    }

    @MainActor func testDeepLinkAndPostAuthenticationResume() {
        let router = AppRouter()
        router.handle(url: URL(string: "onemore://gathering/g-123/space")!, isAuthenticated: false)
        XCTAssertEqual(router.pendingAfterAuthentication, .gathering("g-123"))
        XCTAssertEqual(router.path, [.onboarding("G3")])
        router.resumePending()
        XCTAssertEqual(router.path, [.gathering("g-123")])
    }

    @MainActor func testShareAcquisitionEntersAuthenticationAndResumesLanding() {
        let router = AppRouter()
        router.publicShareToken = "gap-token"
        router.authenticateForShare("gap-token")
        XCTAssertNil(router.publicShareToken)
        XCTAssertEqual(router.pendingAfterAuthentication, .share("gap-token"))
        XCTAssertEqual(router.path, [.onboarding("G3")])
        router.resumePending()
        XCTAssertEqual(router.path, [.share("gap-token")])
    }

    func testTrustRequirementUsesServerDetailsAndKeepsTypedRecoveryTarget() throws {
        let body = APIErrorBody(
            code: "TRUST_LEVEL_REQUIRED",
            message: "此能力要求 T2 及以上",
            details: [
                "required_level": .string("T2"),
                "capability": .string("duo_gathering")
            ],
            requestId: "request-c3"
        )
        let context = TrustRequirementContext(
            error: APIClientError.server(status: 403, body: body),
            recoveryTarget: .gathering("g-high-commitment")
        )
        XCTAssertEqual(context?.requiredLevel, "T2")
        XCTAssertEqual(context?.capabilityTitle, "双人高承诺局")
        XCTAssertEqual(context?.recoveryTarget.route, .gathering("g-high-commitment"))

        let encoded = try JSONEncoder.oneMore.encode(context)
        let decoded = try JSONDecoder.oneMore.decode(TrustRequirementContext?.self, from: encoded)
        XCTAssertEqual(decoded, context)
    }

    @MainActor func testRootTabContractHasExactlyFiveVisualEntries() {
        XCTAssertEqual(RootTab.allCases.map(\.title), ["今天", "活动", "差一个", "消息", "我"])
    }

    func testAPNsPayloadsResolveAndParseEverySupportedBusinessDestination() {
        let cases: [([AnyHashable: Any], String, AppRoute)] = [
            (["screen_id": "E3"], "onemore://screen/E3", .formal(.e3)),
            (["screen_id": "E5"], "onemore://screen/E5", .formal(.e5)),
            (["screen_id": "E6"], "onemore://screen/E6", .formal(.e6)),
            (["screen_id": "E7"], "onemore://screen/E7", .formal(.e7)),
            (["screen_id": "E14"], "onemore://screen/E14", .formal(.e14)),
            (["screen_id": "E16"], "onemore://screen/E16", .formal(.e16)),
            (["screen_id": "G3"], "onemore://screen/G3", .formal(.g3)),
            (["screen_id": "M3"], "onemore://screen/M3", .formal(.m3)),
            (["gathering_id": "g-1"], "onemore://gathering/g-1", .gathering("g-1")),
            (["channel_id": "c-1"], "onemore://channel/c-1", .channel("c-1")),
            (["relation_id": "r-1"], "onemore://relation/r-1", .relation("r-1")),
            (["deep_link": "onemore://relations"], "onemore://relations", .relations),
            (["deep_link": "onemore://trust/progress"], "onemore://trust/progress", .trust),
            (["deep_link": "onemore://auth/reauthorize"], "onemore://auth/reauthorize", .onboarding("G3")),
            (["deep_link": "onemore://auth/reauthorize", "action_id": "a-resume"], "onemore://action/a-resume", .action("a-resume")),
            (["deep_link": "onemore://auth/reauthorize", "gathering_id": "g-resume"], "onemore://gathering/g-resume", .gathering("g-resume")),
            (["payload": ["deep_link": "onemore://relation/r-nested"]], "onemore://relation/r-nested", .relation("r-nested"))
        ]
        for (payload, expectedURL, expectedRoute) in cases {
            let url = NotificationDeepLinkParser.url(from: payload)
            XCTAssertEqual(url?.absoluteString, expectedURL)
            XCTAssertEqual(url.flatMap(AppRoute.parse), expectedRoute)
        }
        XCTAssertNil(NotificationDeepLinkParser.url(from: ["irrelevant": true]))
    }

    func testCalendarPushPayloadParserDistinguishesSyncRefreshAndRemove() {
        XCTAssertEqual(
            CalendarPushEventParser.event(from: [
                "type": "execution_succeeded",
                "gathering_id": "g-sync",
                "calendar_event": ["title": "羽毛球局"]
            ]),
            .sync(gatheringID: "g-sync")
        )
        XCTAssertEqual(
            CalendarPushEventParser.event(from: [
                "payload": [
                    "type": "gathering_rescheduled",
                    "gathering_id": "g-refresh"
                ]
            ]),
            .refresh(gatheringID: "g-refresh")
        )
        XCTAssertEqual(
            CalendarPushEventParser.event(from: [
                "notification_type": "calendar_revoked",
                "gathering_id": "g-remove"
            ]),
            .remove(gatheringID: "g-remove")
        )
    }

    func testWebSocketForegroundLifecycleReturnsToIdle() async {
        let auth = AuthManager(keychain: .init(service: "tests.ws.lifecycle.\(UUID().uuidString)"))
        let socket = WebSocketClient(baseURL: URL(string: "wss://socket.test")!, auth: auth)
        await socket.setForeground(false)
        let state = await socket.state
        if case .idle = state {} else { XCTFail("Background socket must be idle") }
        await socket.setForeground(true)
    }

    func testServerStateMappingNeverInfers() throws {
        for state in GatheringStatus.allCases where state != .unknown {
            let encoded = try JSONEncoder().encode(state.rawValue)
            XCTAssertEqual(try JSONDecoder().decode(GatheringStatus.self, from: encoded), state)
        }
    }
}
