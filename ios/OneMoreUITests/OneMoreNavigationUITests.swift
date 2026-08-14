import XCTest

final class OneMoreNavigationUITests: XCTestCase {
    private var app: XCUIApplication!

    private struct LiveScenario {
        let gatheringID: String
        let startAt: Date
        let endAt: Date
        let token: String
    }

    private static let apiISO: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    private func launchDefault(userID: String = "u_demo_1", extra: [String] = []) {
        app.terminate()
        app.launchArguments = [
            "-UI_TESTING", "YES",
            "-DevUserIDOverride", userID,
            "-UIAccessibilityReduceMotionEnabled", "YES"
        ] + extra
        app.launch()
    }

    private func launchProduction(_ id: String, userID: String = "u_demo_1") {
        launchDefault(userID: userID, extra: ["-ProductionScreenID", id])
        let concreteIDs = [
            "B2": "screen-B2-hermes",
            "B3": "screen-B3-timetable",
            "B4": "screen-B4-assignments",
            "B5": "screen-B5-gym",
            "B6": "screen-B6-room",
            "B7": "screen-B7-events",
            "B8": "screen-B8-campus-query",
            "B9": "screen-B9-transit-reference",
            "B10": "screen-B10-scene-trigger",
            "M2": "screen-M2-profile-editor",
            "M4": "screen-M4-grants",
            "M5": "screen-M5-privacy",
            "M6": "screen-M6-matching-preferences",
            "M7": "screen-M7-notification-settings",
            "M8": "screen-M8-block-list",
            "M9": "screen-M9-appeals"
        ]
        XCTAssertTrue(
            any(concreteIDs[id] ?? "screen-\(id)").waitForExistence(timeout: 6),
            "Production route \(id) did not launch"
        )
    }

    private func launchPrototype(_ id: String) {
        app.terminate()
        app.launchArguments = ["-UI_TESTING", "YES", "-UIAccessibilityReduceMotionEnabled", "YES", "-PrototypeScreenID", id]
        app.launch()
        XCTAssertTrue(any("prototype-screen-\(id)").waitForExistence(timeout: 4), "Prototype \(id) did not launch")
    }

    private func launchState(_ state: String) {
        app.terminate()
        app.launchArguments = ["-UI_TESTING", "YES", "-StateEvidence", state]
        app.launch()
        XCTAssertTrue(any("state-evidence-\(state)").waitForExistence(timeout: 4), "State \(state) did not launch")
    }

    private func any(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any)[identifier]
    }

    @discardableResult
    private func tapButton(_ title: String, swipes: Int = 8) -> XCUIElement {
        var button = app.buttons[title]
        if !button.exists {
            let containing = app.buttons.containing(.staticText, identifier: title).firstMatch
            if containing.exists { button = containing }
        }
        for _ in 0..<swipes where !button.isHittable { app.swipeUp(); Thread.sleep(forTimeInterval: 0.08) }
        XCTAssertTrue(button.waitForExistence(timeout: 2), "Missing CTA \(title)")
        XCTAssertTrue(button.isEnabled, "Disabled CTA \(title) did not expose a disabled reason in this flow")
        XCTAssertTrue(button.isHittable, "CTA \(title) is not reachable")
        button.tap()
        return button
    }

    private func nudgeScroll(up: Bool) {
        let startY: CGFloat = up ? 0.72 : 0.28
        let endY: CGFloat = up ? 0.57 : 0.43
        app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: startY))
            .press(
                forDuration: 0.01,
                thenDragTo: app.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: endY))
            )
        Thread.sleep(forTimeInterval: 0.08)
    }

    private func assertPrototype(_ id: String, timeout: TimeInterval = 4) {
        XCTAssertTrue(any("prototype-screen-\(id)").waitForExistence(timeout: timeout), "Expected \(id)")
    }

    private func apiData(
        _ path: String,
        method: String = "GET",
        userID: String = "u_demo_1",
        body: [String: Any]? = nil,
        extraHeaders: [String: String] = [:],
        includeIdempotencyKey: Bool = true,
        expectedStatus: Set<Int> = [200]
    ) -> Any {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:8000\(path)")!)
        request.httpMethod = method
        request.setValue(userID, forHTTPHeaderField: "X-User-ID")
        if includeIdempotencyKey {
            request.setValue(UUID().uuidString, forHTTPHeaderField: "Idempotency-Key")
        }
        for (key, value) in extraHeaders { request.setValue(value, forHTTPHeaderField: key) }
        if let body {
            request.httpBody = try! JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        let semaphore = DispatchSemaphore(value: 0)
        var responseStatus = 0
        var responseData = Data()
        var responseError: Error?
        URLSession.shared.dataTask(with: request) { data, response, error in
            responseStatus = (response as? HTTPURLResponse)?.statusCode ?? 0
            responseData = data ?? Data()
            responseError = error
            semaphore.signal()
        }.resume()
        XCTAssertEqual(semaphore.wait(timeout: .now() + 25), .success, "API timed out: \(path)")
        XCTAssertNil(responseError, "API transport failed: \(path)")
        XCTAssertTrue(expectedStatus.contains(responseStatus), "Unexpected \(responseStatus) for \(path): \(String(decoding: responseData, as: UTF8.self))")
        let object = try! JSONSerialization.jsonObject(with: responseData) as! [String: Any]
        return object["data"] as Any
    }

    private func makeGapShareToken() -> String {
        // The login fixture resumes u_demo_1 through the real auth endpoints;
        // use a different same-college owner so this is an actual acquisition,
        // not the owner opening their own share card.
        let compiled = apiData(
            "/intent/compile",
            method: "POST",
            userID: "u_demo_2",
            body: ["text": "周六晚上一起打羽毛球，4人 UI \(UUID().uuidString)"]
        ) as! [String: Any]
        let card = compiled["card"] as! [String: Any]
        let published = apiData(
            "/intent/publish",
            method: "POST",
            userID: "u_demo_2",
            body: ["card_id": card["id"] as! String],
            expectedStatus: [201]
        ) as! [String: Any]
        let share = apiData(
            "/gatherings/\(published["gathering_id"] as! String)/share",
            method: "POST",
            userID: "u_demo_2",
            expectedStatus: [201]
        ) as! [String: Any]
        return share["share_token"] as! String
    }

    private func launchGathering(_ id: String) {
        launchDefault(extra: ["-ProductionDeepLink", "onemore://gathering/\(id)"])
        XCTAssertTrue(
            any("screen-E3-gathering-detail").waitForExistence(timeout: 12),
            "Live gathering \(id) did not launch"
        )
    }

    /// Keep each UI scenario isolated while exercising only normal member APIs.
    /// Completed history is deliberately retained because it is product evidence.
    private func cleanupPendingGatherings() {
        let mutableStatuses: Set<String> = [
            "Pooling", "Tentative", "Confirmed", "Previewed", "Executed", "Active",
            "RecurrencePending"
        ]
        for index in 1...4 {
            let userID = "u_demo_\(index)"
            let mine = apiData("/gatherings/mine", userID: userID) as! [[String: Any]]
            for item in mine where mutableStatuses.contains(item["status"] as? String ?? "") {
                guard let id = item["id"] as? String else { continue }
                _ = apiData(
                    "/gatherings/\(id)/leave",
                    method: "POST",
                    userID: userID,
                    body: ["reason": "UI E2E fixture cleanup"],
                    expectedStatus: [200, 403, 404, 409]
                )
            }
        }
    }

    private func competitionID(named name: String) -> String {
        let competitions = apiData("/competitions") as! [[String: Any]]
        let item = competitions.first { ($0["name"] as? String) == name }
        XCTAssertNotNil(item, "Missing production competition \(name)")
        return item!["id"] as! String
    }

    /// Builds an otherwise ordinary live scenario through compile → publish →
    /// server matching. The short explicit window lets the completion boundary
    /// be exercised in a bounded UI test without mutating the database directly.
    private func createMatchedScenario(
        text: String,
        competitionID: String? = nil,
        startDelay: TimeInterval = 180,
        duration: TimeInterval = 180
    ) -> LiveScenario {
        cleanupPendingGatherings()
        let token = "UIE2E-\(UUID().uuidString.prefix(8))"
        let startAt = Date().addingTimeInterval(startDelay)
        let endAt = startAt.addingTimeInterval(duration)
        let availability = "\(Self.apiISO.string(from: startAt))|\(Self.apiISO.string(from: endAt))"

        for index in 1...4 {
            var request: [String: Any] = [
                "text": "\(token) \(text)",
                "clarification_round": 1,
                "answers": ["availability": availability]
            ]
            if let competitionID { request["competition_id"] = competitionID }
            let compiled = apiData(
                "/intent/compile",
                method: "POST",
                userID: "u_demo_\(index)",
                body: request
            ) as! [String: Any]
            XCTAssertEqual(compiled["needs_clarification"] as? Bool, false)
            let card = compiled["card"] as! [String: Any]
            _ = apiData(
                "/intent/publish",
                method: "POST",
                userID: "u_demo_\(index)",
                body: ["card_id": card["id"] as! String],
                expectedStatus: [201]
            )
        }

        let matched = apiData(
            "/internal/matching/run",
            method: "POST",
            extraHeaders: ["X-Admin-Token": "change-me"]
        ) as! [String: Any]
        XCTAssertGreaterThanOrEqual(matched["formed"] as? Int ?? 0, 1)
        let mine = apiData("/gatherings/mine") as! [[String: Any]]
        let gathering = mine.first {
            (($0["goal"] as? String)?.contains(token) == true) &&
                ($0["status"] as? String) == "Tentative"
        }
        XCTAssertNotNil(gathering, "Matching did not form the unique live scenario")
        let gatheringID = gathering!["id"] as! String
        for index in 2...4 {
            _ = apiData(
                "/gatherings/\(gatheringID)/confirm",
                method: "POST",
                userID: "u_demo_\(index)",
                body: ["confirmed": true]
            )
        }
        return LiveScenario(
            gatheringID: gatheringID,
            startAt: startAt,
            endAt: endAt,
            token: token
        )
    }

    private func actionID(for gatheringID: String, timeout: TimeInterval = 15) -> String {
        let deadline = Date().addingTimeInterval(timeout)
        repeat {
            let detail = apiData("/gatherings/\(gatheringID)") as! [String: Any]
            if let id = detail["action_id"] as? String { return id }
            Thread.sleep(forTimeInterval: 0.25)
        } while Date() < deadline
        XCTFail("No action preview was attached to gathering \(gatheringID)")
        return "missing-action"
    }

    private func authorizeAllMembers(actionID: String) {
        let action = apiData("/actions/\(actionID)") as! [String: Any]
        let snapshotHash = action["snapshot_hash"] as! String
        for index in 1...4 {
            _ = apiData(
                "/actions/\(actionID)/authorization",
                method: "POST",
                userID: "u_demo_\(index)",
                body: ["authorized": true, "snapshot_hash": snapshotHash]
            )
        }
    }

    private func ensureCampusActionTrust() {
        let order = ["T0": 0, "T1": 1, "T2": 2, "T3": 3, "T4": 4]
        for index in 1...4 {
            let userID = "u_demo_\(index)"
            _ = apiData(
                "/internal/trust/\(userID)/organizer-verification",
                method: "POST",
                userID: userID,
                body: ["verified": true],
                extraHeaders: ["X-Admin-Token": "change-me"]
            )
            let progress = apiData("/trust/me", userID: userID) as! [String: Any]
            let level = progress["level"] as? String ?? "T0"
            XCTAssertGreaterThanOrEqual(order[level] ?? 0, order["T2"]!, "Campus action fixture requires T2+")
        }
    }

    /// Confirms the owner, consumes a fresh Hermes-signed booking option,
    /// previews, gathers four independent authorizations, and executes in UI.
    private func driveConfirmedGatheringThroughAction(_ scenario: LiveScenario) {
        ensureCampusActionTrust()
        launchGathering(scenario.gatheringID)
        tapButton("确认参加", swipes: 10)
        // The first confirmed gathering may surface the one-time system
        // notification prompt. XCTest dismisses it, but iOS intentionally
        // drops the underlying tap, so retry the same idempotent member action.
        let bookingBridge = app.buttons["查询真实可预约场地"]
        if !bookingBridge.waitForExistence(timeout: 5), app.buttons["确认参加"].exists {
            tapButton("确认参加", swipes: 10)
        }
        XCTAssertTrue(
            bookingBridge.waitForExistence(timeout: 15),
            "Confirmed state did not expose the server booking bridge"
        )
        tapButton("查询真实可预约场地", swipes: 12)
        XCTAssertTrue(any("gathering-booking-options").waitForExistence(timeout: 15))
        let previewButton = app.buttons["生成校园写操作预览"]
        for _ in 0..<3 where !previewButton.exists {
            let option = app.buttons.matching(identifier: "gathering-booking-option").firstMatch
            XCTAssertTrue(option.waitForExistence(timeout: 5), "No fresh Hermes option was rendered")
            for _ in 0..<12 where !option.isHittable {
                nudgeScroll(up: true)
            }
            XCTAssertTrue(option.isEnabled)
            XCTAssertTrue(option.isHittable)
            option.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
                .press(forDuration: 0.12)
            let deadline = Date().addingTimeInterval(6)
            while Date() < deadline, !previewButton.exists {
                RunLoop.current.run(until: Date().addingTimeInterval(0.1))
            }
        }
        XCTAssertTrue(previewButton.waitForExistence(timeout: 15))
        tapButton("生成校园写操作预览", swipes: 12)
        XCTAssertTrue(any("gathering-action-preview").waitForExistence(timeout: 15))
        tapButton("核对无误，分别确认", swipes: 12)

        let id = actionID(for: scenario.gatheringID)
        authorizeAllMembers(actionID: id)
        launchGathering(scenario.gatheringID)
        XCTAssertTrue(any("gathering-action-preview").waitForExistence(timeout: 12))
        tapButton("全员已确认，由我执行", swipes: 12)
        XCTAssertTrue(
            any("gathering-action-result").waitForExistence(timeout: 20),
            "Campus action did not reach the live execution result"
        )
        XCTAssertTrue(app.staticTexts["执行成功；阿凑已退场。"].waitForExistence(timeout: 10))
    }

    private func driveCurrentIntentToPooling() {
        let clarification = any("screen-D2-clarification")
        let publish = app.buttons["intent-publish-button"]
        let compile = app.buttons["intent-compile-button"]
        // Immediately after a preset pushes D1, XCTest can report the compile
        // control as hittable while the navigation transition consumes a
        // synthesized gesture. Retry normal and coordinate taps until SwiftUI
        // actually removes the editing CTA (the synchronous `.compiling`
        // transition), rather than assuming that XCTest delivered the event.
        for attempt in 0..<6 where compile.exists {
            XCTAssertTrue(compile.waitForExistence(timeout: 3))
            XCTAssertTrue(compile.isEnabled)
            XCTAssertTrue(compile.isHittable)
            Thread.sleep(forTimeInterval: 0.25)
            if attempt.isMultiple(of: 3) {
                compile.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
                    .press(forDuration: 0.12)
            } else if attempt.isMultiple(of: 2) {
                compile.tap()
            } else {
                compile.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
            }
            let deadline = Date().addingTimeInterval(2)
            while Date() < deadline, compile.exists {
                RunLoop.current.run(until: Date().addingTimeInterval(0.1))
            }
        }
        XCTAssertFalse(compile.exists, "Compile CTA never dispatched its editing → compiling transition")
        let compiledDeadline = Date().addingTimeInterval(20)
        while Date() < compiledDeadline, !clarification.exists, !publish.exists {
            RunLoop.current.run(until: Date().addingTimeInterval(0.1))
        }
        XCTAssertTrue(clarification.exists || publish.exists, "Compile did not reach clarification or preview")
        if clarification.exists {
            let continueButton = app.buttons["intent-clarification-continue"]
            for attempt in 0..<6 where continueButton.exists {
                XCTAssertTrue(continueButton.waitForExistence(timeout: 3))
                XCTAssertTrue(continueButton.isEnabled)
                XCTAssertTrue(continueButton.isHittable)
                Thread.sleep(forTimeInterval: 0.25)
                if attempt.isMultiple(of: 3) {
                    continueButton.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5))
                        .press(forDuration: 0.12)
                } else if attempt.isMultiple(of: 2) {
                    continueButton.tap()
                } else {
                    continueButton.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
                }
                let deadline = Date().addingTimeInterval(2)
                while Date() < deadline, continueButton.exists {
                    RunLoop.current.run(until: Date().addingTimeInterval(0.1))
                }
            }
            XCTAssertFalse(continueButton.exists, "Clarification CTA never dispatched its compiling transition")
        }
        XCTAssertTrue(publish.waitForExistence(timeout: 15))
        tapButton("确认发布", swipes: 12)
        XCTAssertTrue(app.buttons["查看招募状态"].waitForExistence(timeout: 15))
        tapButton("查看招募状态", swipes: 6)
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 12))
        XCTAssertTrue(app.staticTexts["匿名招募中"].waitForExistence(timeout: 8))
    }

    /// Completes account-scoped first-use setup only when this simulator has
    /// no prior completion bit. This keeps returning-user deep-link tests
    /// independent from XCTest ordering and persisted simulator state.
    private func completeFirstUseIfPresented() {
        guard any("screen-A4-grants").waitForExistence(timeout: 6) else { return }
        tapButton("保存授权并读取身份事实", swipes: 8)
        XCTAssertTrue(any("screen-A5-A6-facts").waitForExistence(timeout: 15))
        tapButton("身份事实无误", swipes: 8)
        XCTAssertTrue(any("screen-A7-social").waitForExistence(timeout: 6))
        tapButton("开启并继续", swipes: 8)
        skipFirstUseTasteIfPresented()
        XCTAssertTrue(any("screen-A7-ready").waitForExistence(timeout: 12))
        tapButton("进入今天", swipes: 8)
    }

    /// Optional Douyin taste import sits between social opt-in and ready.
    private func skipFirstUseTasteIfPresented() {
        XCTAssertTrue(any("screen-first-use-taste").waitForExistence(timeout: 12), "first-use taste step missing")
        if any("first-use-skip-taste").waitForExistence(timeout: 6) {
            let skip = any("first-use-skip-taste")
            for _ in 0..<8 where !skip.isHittable {
                app.swipeUp()
                Thread.sleep(forTimeInterval: 0.08)
            }
            skip.tap()
            return
        }
        if any("first-use-taste-continue").waitForExistence(timeout: 4) {
            any("first-use-taste-continue").tap()
            return
        }
        tapButton("暂时跳过，稍后再贴", swipes: 8)
    }

    /// Creates an isolated, verified T1 account through the same fake-CAS
    /// session/binding path used by the development authentication screen.
    /// No trust row or completion counter is edited by the test.
    private func createIsolatedTrustUser(role: String) -> String {
        let suffix = UUID().uuidString.lowercased()
        let userID = "ui_\(role)_\(suffix.prefix(12))"
        let login = apiData(
            "/auth/session",
            method: "POST",
            userID: userID,
            body: [
                "device_install_id": "ui-device-\(suffix)",
                "resume_user_id": userID
            ],
            includeIdempotencyKey: false,
            expectedStatus: [202]
        ) as! [String: Any]
        let sessionID = login["id"] as! String
        let redemption = login["redemption_token"] as! String
        _ = apiData(
            "/auth/session/\(sessionID)/demo-complete",
            method: "POST",
            userID: userID,
            body: [:],
            extraHeaders: [
                "X-Login-Redemption": redemption,
                "X-Demo-Campus-Subject": "ui-\(role)-\(suffix)"
            ],
            includeIdempotencyKey: false
        )
        _ = apiData(
            "/me/privacy",
            method: "PATCH",
            userID: userID,
            body: [
                "social_enabled": true,
                "minimum_group_size": ["recover", "highowner"].contains(role) ? 2 : 3
            ]
        )
        let progress = apiData("/trust/me", userID: userID) as! [String: Any]
        XCTAssertEqual(progress["level"] as? String, "T1")
        return userID
    }

    private func createHighCommitmentGathering(ownerID: String) -> String {
        _ = apiData(
            "/internal/trust/\(ownerID)/organizer-verification",
            method: "POST",
            userID: ownerID,
            body: ["verified": true],
            extraHeaders: ["X-Admin-Token": "change-me"]
        )
        let created = apiData(
            "/gatherings/initiate",
            method: "POST",
            userID: ownerID,
            body: [
                "title": "T2 双人高承诺任务 \(UUID().uuidString.prefix(8))",
                "goal": "验证服务端准入、低风险履约与原任务恢复",
                "gathering_type": "项目共创",
                "mode": "similar",
                "min_size": 2,
                "target_size": 2,
                "cross_college": false,
                "required_roles": []
            ],
            expectedStatus: [201]
        ) as! [String: Any]
        XCTAssertEqual(created["required_trust_level"] as? String, "T2")
        return created["id"] as! String
    }

    private func createLowRiskPool(
        ownerID: String,
        startDelay: TimeInterval,
        duration: TimeInterval
    ) -> (id: String, titleToken: String, endAt: Date) {
        let token = "LOW-RISK-\(UUID().uuidString.prefix(8))"
        let startAt = Date().addingTimeInterval(startDelay)
        let endAt = startAt.addingTimeInterval(duration)
        let availability = "\(Self.apiISO.string(from: startAt))|\(Self.apiISO.string(from: endAt))"
        let compiled = apiData(
            "/intent/compile",
            method: "POST",
            userID: ownerID,
            body: [
                "text": "\(token) 同校三人安静自习，3人",
                "clarification_round": 1,
                "answers": ["availability": availability]
            ]
        ) as! [String: Any]
        XCTAssertEqual(compiled["needs_clarification"] as? Bool, false)
        let card = compiled["card"] as! [String: Any]
        let published = apiData(
            "/intent/publish",
            method: "POST",
            userID: ownerID,
            body: ["card_id": card["id"] as! String],
            expectedStatus: [201]
        ) as! [String: Any]
        return (published["gathering_id"] as! String, token, endAt)
    }

    private func finishLowRiskGathering(
        _ id: String,
        endAt: Date,
        members: [String]
    ) {
        for userID in members {
            _ = apiData(
                "/gatherings/\(id)/confirm",
                method: "POST",
                userID: userID,
                body: ["confirmed": true]
            )
        }
        let wait = max(0, endAt.timeIntervalSinceNow + 0.4)
        if wait > 0 { Thread.sleep(forTimeInterval: wait) }
        _ = apiData("/gatherings/\(id)", userID: members[0])
        for userID in members {
            _ = apiData(
                "/gatherings/\(id)/complete",
                method: "POST",
                userID: userID,
                body: ["completed": true]
            )
        }
    }

    /// Creates a completed shared experience through ordinary public member
    /// APIs. Flow 8 must not consume seed data or rely on Flow 2 having run.
    private func createCompletedRelationEvidence() -> String {
        let scenario = createMatchedScenario(
            text: "搭子关系共同经历，4人",
            startDelay: 5,
            duration: 2
        )
        _ = apiData(
            "/gatherings/\(scenario.gatheringID)/confirm",
            method: "POST",
            body: ["confirmed": true]
        )
        let wait = max(0, scenario.endAt.timeIntervalSinceNow + 0.5)
        if wait > 0 { Thread.sleep(forTimeInterval: wait) }
        // A detail read applies the normal Confirmed → Active time boundary.
        _ = apiData("/gatherings/\(scenario.gatheringID)")
        for index in 1...4 {
            _ = apiData(
                "/gatherings/\(scenario.gatheringID)/complete",
                method: "POST",
                userID: "u_demo_\(index)",
                body: ["completed": true]
            )
        }
        let relations = apiData("/relations") as! [[String: Any]]
        let relation = relations.first { !(($0["experiences"] as? [[String: Any]]) ?? []).isEmpty }
        XCTAssertNotNil(relation, "Normal completion did not create a fact-only relation")
        return relation!["id"] as! String
    }

    func testFiveMainEntriesAreReachable() {
        launchDefault()
        for title in ["今天", "比赛", "差一个", "消息", "我"] {
            let tab = app.tabBars.buttons[title]
            XCTAssertTrue(tab.waitForExistence(timeout: 5), "Missing tab \(title)")
            tab.tap()
        }
        XCTAssertTrue(any("screen-M1-profile").waitForExistence(timeout: 3))
    }

    func testSecondaryBusinessEntriesFromToday() {
        launchDefault()
        app.tabBars.buttons["今天"].tap()
        tapButton("我的局", swipes: 10)
        XCTAssertTrue(app.staticTexts["我的局"].waitForExistence(timeout: 5))
    }

    func testVersionedSYSUReferenceIsConsumedByProductionTools() {
        launchProduction("B5")
        XCTAssertTrue(any("reference-venue-directory").waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts.matching(
            NSPredicate(format: "label CONTAINS %@", "sysu-campus-reference-v1.1")
        ).firstMatch.exists)

        launchProduction("B9")
        XCTAssertTrue(any("reference-transit-section-card").waitForExistence(timeout: 8))
        XCTAssertTrue(app.staticTexts["典型通勤约 30 分钟"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["节次 08:00–08:45"].exists)
    }

    func testCompetitionListUsesTwentyFourProductionItems() {
        launchDefault()
        app.tabBars.buttons["比赛"].tap()
        XCTAssertTrue(app.staticTexts["24 场可行动赛事"].waitForExistence(timeout: 8))
        XCTAssertFalse(app.staticTexts["21 场可行动赛事"].exists)
        XCTAssertFalse(app.staticTexts["2026 校园创新应用大赛"].exists)
    }

    func testLiveFastAPIIntentCompilePublishDetailAndLeave() {
        launchDefault()
        app.tabBars.buttons["差一个"].tap()

        let input = app.textViews["intent-text-input"]
        XCTAssertTrue(input.waitForExistence(timeout: 5))
        input.tap()
        input.typeText("周六晚上一起打羽毛球，4人")
        let done = app.toolbars.buttons["完成"]
        XCTAssertTrue(done.waitForExistence(timeout: 3))
        done.tap()

        tapButton("让阿凑理解", swipes: 10)
        let publish = app.buttons["确认发布"]
        XCTAssertTrue(publish.waitForExistence(timeout: 15), "FastAPI compile did not return an intent preview")
        publish.tap()

        let viewStatus = app.buttons["查看招募状态"]
        XCTAssertTrue(viewStatus.waitForExistence(timeout: 15), "FastAPI publish did not return a gathering")
        viewStatus.tap()

        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 10))
        let leave = app.buttons["gathering-leave-action"]
        let usableBottom = app.frame.maxY - 150
        for _ in 0..<18 {
            if leave.exists,
               leave.frame.minY > 90,
               leave.frame.maxY < usableBottom {
                break
            }
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(leave.waitForExistence(timeout: 4), "Stable leave CTA was not rendered")
        XCTAssertTrue(leave.isEnabled, "Leave CTA unexpectedly disabled")
        XCTAssertGreaterThan(leave.frame.minY, 90, "Leave CTA is under navigation chrome")
        XCTAssertLessThan(leave.frame.maxY, usableBottom, "Leave CTA is under the tab bar")
        leave.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        let confirm = app.buttons["确认退出"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 4), "Leave confirmation did not appear")
        confirm.tap()
        XCTAssertTrue(app.staticTexts["已退出这个局"].waitForExistence(timeout: 10))
    }

    func testDynamicTypeVoiceLabelsAndReduceMotionLaunchSmoke() {
        launchDefault(extra: ["-UIPreferredContentSizeCategoryName", "UICTContentSizeCategoryAccessibilityLarge", "-UIAccessibilityReduceMotionEnabled", "YES"])
        XCTAssertTrue(app.tabBars.buttons["今天"].waitForExistence(timeout: 5))
        XCTAssertTrue(any("screen-B1-today").exists)
        XCTAssertTrue(app.staticTexts["今天，差一个就成局"].exists)
    }

    func testProductionBusinessEntryGraphNavigatesConcreteSecondaryScreens() {
        let todayEntries = [
            ("today-timetable", "我的课表", "screen-B3-timetable"),
            ("today-assignments", "作业 DDL", "screen-B4-assignments"),
            ("today-room", "图书馆研讨室", "screen-B6-room"),
            ("today-gym", "体育场馆", "screen-B5-gym"),
            ("today-events", "校园活动", "screen-B7-events"),
            ("today-research", "组会与课题", "screen-B8-campus-query"),
            ("today-transit", "班车", "screen-B9-transit-reference"),
            ("today-public-gatherings", "公开局", "screen-C1-public-gatherings"),
            ("today-my-gatherings", "我的局", "screen-E1-my-gatherings"),
            ("today-relations", "搭子关系", "screen-E15-relations")
        ]
        for (buttonIdentifier, title, screenIdentifier) in todayEntries {
            launchDefault()
            let entry = app.buttons[buttonIdentifier]
            let usableBottom = app.frame.maxY - 100
            for _ in 0..<24 {
                if entry.exists,
                   entry.frame.minY > 90,
                   entry.frame.maxY < usableBottom {
                    break
                }
                if entry.exists, entry.frame.minY <= 90 {
                    nudgeScroll(up: false)
                } else {
                    nudgeScroll(up: true)
                }
            }
            XCTAssertTrue(entry.waitForExistence(timeout: 4), "Missing production entry \(title)")
            XCTAssertGreaterThan(entry.frame.minY, 90, "Production entry is under navigation chrome: \(title)")
            XCTAssertLessThan(entry.frame.maxY, usableBottom, "Production entry is under the tab bar: \(title)")
            entry.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
            XCTAssertTrue(any(screenIdentifier).waitForExistence(timeout: 10), title)
        }

        let profileEntries = [
            ("画像与能力", "screen-M2-profile-editor"),
            ("信任进度", "screen-M3-trust"),
            ("授权管理", "screen-M4-grants"),
            ("隐私与安全", "screen-M5-privacy"),
            ("匹配偏好", "screen-M6-matching-preferences"),
            ("通知与日历", "screen-M7-notification-settings"),
            ("黑名单", "screen-M8-block-list"),
            ("信任申诉", "screen-M9-appeals"),
            ("数据导出与注销", "screen-M10-account")
        ]
        for (title, identifier) in profileEntries {
            launchDefault()
            app.tabBars.buttons["我"].tap()
            tapButton(title, swipes: 16)
            XCTAssertTrue(any(identifier).waitForExistence(timeout: 10), title)
        }
    }

    func testThirtySixReturnedBoardsRemainReachableForFidelityEvidence() {
        let ids = [
            "A2","A3","A4","A5","A6","A7","B1","C1","B12","B12.1","B12.2","MSG",
            "D1","D2","D3","D4","E3","E5","E6","E7","E14","B5","B5.1","E9","E10",
            "B4","B4.1","B7","B7.1","G2","C4","E1","E16","E17","M1","M3"
        ]
        XCTAssertEqual(ids.count, 36)
        for id in ids { launchPrototype(id) }
    }

    func testLoadingEmptyErrorOfflinePermissionSessionDuplicateAndStaleStates() {
        for state in ["loading", "empty", "network-error", "offline", "permission-denied", "session-expired", "duplicate-tap", "stale-state"] {
            launchState(state)
        }
    }

    func testFlow1FirstUseAuthenticationUsesLiveFastAPI() {
        launchDefault(extra: [
            "-ForceSignedOut", "YES",
            "-ForceFirstUse", "YES",
            "-AutoCompleteLogin", "YES",
            "-LoginResumeUserID", "u_demo_1"
        ])
        XCTAssertTrue(app.tabBars.buttons["差一个"].waitForExistence(timeout: 6))
        app.tabBars.buttons["差一个"].tap()
        XCTAssertTrue(any("screen-A2-auth-intro").waitForExistence(timeout: 6))
        tapButton("使用统一身份认证")
        XCTAssertTrue(any("screen-A3-real-login").waitForExistence(timeout: 4))
        tapButton("生成认证二维码")
        XCTAssertTrue(any("screen-A4-grants").waitForExistence(timeout: 20), "A4 did not follow live authentication")
        tapButton("保存授权并读取身份事实", swipes: 8)
        XCTAssertTrue(any("screen-A5-A6-facts").waitForExistence(timeout: 15), "A5/A6 facts did not load")
        tapButton("身份事实无误", swipes: 8)
        XCTAssertTrue(any("screen-A7-social").waitForExistence(timeout: 5))
        tapButton("开启并继续", swipes: 8)
        skipFirstUseTasteIfPresented()
        XCTAssertTrue(any("screen-A7-ready").waitForExistence(timeout: 10))
        tapButton("进入今天", swipes: 8)
        XCTAssertTrue(app.tabBars.buttons["今天"].waitForExistence(timeout: 10), "A7 did not finish at B1")
        XCTAssertTrue(any("screen-B1-today").waitForExistence(timeout: 10))
    }

    func testFlow2CompetitionTeamFormationUsesProductionScreens() {
        let competitionName = "2026年全国大学生数智链应用大赛"
        let competitionID = competitionID(named: competitionName)
        launchDefault()
        app.tabBars.buttons["比赛"].tap()
        XCTAssertTrue(any("screen-B12-competitions").waitForExistence(timeout: 6))
        let competition = any("competition-\(competitionID)")
        for _ in 0..<20 where !competition.isHittable {
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(competition.waitForExistence(timeout: 4), "Missing production competition \(competitionName)")
        XCTAssertTrue(competition.isHittable, "Production competition is not reachable")
        competition.tap()
        XCTAssertTrue(any("screen-B12.1-competition-detail").waitForExistence(timeout: 8))
        tapButton("找队友", swipes: 10)
        XCTAssertTrue(any("screen-B12.2-table").waitForExistence(timeout: 6))

        let scenario = createMatchedScenario(
            text: "数智链比赛组队，4人",
            competitionID: competitionID,
            startDelay: 60,
            duration: 65
        )
        driveConfirmedGatheringThroughAction(scenario)

        let channelCTA = app.buttons["gathering-collaboration-space"]
        let usableBottom = app.frame.maxY - 150
        for _ in 0..<18 {
            if channelCTA.exists,
               channelCTA.frame.minY > 90,
               channelCTA.frame.maxY < usableBottom {
                break
            }
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(channelCTA.waitForExistence(timeout: 4), "E7 channel CTA was not rendered")
        XCTAssertGreaterThan(channelCTA.frame.minY, 90, "E7 channel CTA is hidden under the navigation chrome")
        XCTAssertLessThan(channelCTA.frame.maxY, usableBottom, "E7 channel CTA is hidden under the tab bar")
        channelCTA.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        XCTAssertTrue(any("screen-E14-channel").waitForExistence(timeout: 12))
        let message = "本次分工已确认 \(scenario.token)"
        let input = any("channel-message-input")
        XCTAssertTrue(input.waitForExistence(timeout: 8), "E14 message input unavailable")
        input.tap()
        input.typeText(message)
        let send = any("channel-send-message")
        XCTAssertTrue(send.isEnabled)
        send.tap()
        XCTAssertTrue(
            app.descendants(matching: .any).matching(
                NSPredicate(format: "label CONTAINS %@", message)
            ).firstMatch.waitForExistence(timeout: 12),
            "The human channel message was not persisted and rendered"
        )

        let mention = "@阿凑 日历提醒 \(scenario.token)"
        XCTAssertTrue(input.waitForExistence(timeout: 5))
        input.tap()
        input.typeText(mention)
        XCTAssertTrue(send.isEnabled)
        send.tap()
        let azouReply = "我已准备日历入口；只有执行成功的局才会生成日历事件。"
        XCTAssertTrue(
            app.descendants(matching: .any).matching(
                NSPredicate(format: "label CONTAINS %@", azouReply)
            ).firstMatch.waitForExistence(timeout: 12),
            "The server-owned @阿凑 response was not rendered"
        )

        let wait = max(0, scenario.endAt.timeIntervalSinceNow + 1.0)
        if wait > 0 { Thread.sleep(forTimeInterval: wait) }
        for index in 2...4 {
            _ = apiData(
                "/gatherings/\(scenario.gatheringID)/complete",
                method: "POST",
                userID: "u_demo_\(index)",
                body: ["completed": true]
            )
        }
        launchGathering(scenario.gatheringID)
        tapButton("确认本次已完成", swipes: 14)
        XCTAssertTrue(app.buttons["再来一次"].waitForExistence(timeout: 15))
        tapButton("再来一次", swipes: 12)
        XCTAssertTrue(any("screen-E10-recurrence-choice").waitForExistence(timeout: 8))
        tapButton("原班复局", swipes: 8)
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 15))
        XCTAssertTrue(
            app.staticTexts.matching(
                NSPredicate(format: "label CONTAINS %@", scenario.token)
            ).firstMatch.waitForExistence(timeout: 8)
        )
    }

    func testFlow3NaturalLanguageIntentUsesLiveCompileAndPublish() {
        launchDefault()
        app.tabBars.buttons["差一个"].tap()
        let input = app.textViews["intent-text-input"]
        XCTAssertTrue(input.waitForExistence(timeout: 5))
        input.tap()
        input.typeText("周六晚上一起打羽毛球，4人")
        if app.toolbars.buttons["完成"].waitForExistence(timeout: 2) { app.toolbars.buttons["完成"].tap() }
        tapButton("让阿凑理解", swipes: 10)
        let publish = app.buttons["确认发布"]
        XCTAssertTrue(publish.waitForExistence(timeout: 15))
        publish.tap()
        XCTAssertTrue(app.buttons["查看招募状态"].waitForExistence(timeout: 15))
        app.buttons["查看招募状态"].tap()
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 12))
        XCTAssertTrue(app.staticTexts["匿名招募中"].waitForExistence(timeout: 8))
    }

    func testFlow4SportsCompanionUsesProductionVenueCTA() {
        // Keep the abandoned preset draft on a different account scope from
        // Flow 5's assignment owner. The subsequent u_demo_1 gathering launch
        // then exercises the real account-scope switch and prevents a stale
        // recovery journal from racing the next production intent composer.
        launchProduction("B5", userID: "u_demo_2")
        tapButton("用这个时段找运动搭子", swipes: 10)
        XCTAssertTrue(any("screen-D1-intent").waitForExistence(timeout: 8))
        XCTAssertTrue(app.textViews["intent-text-input"].value as? String != "")

        let scenario = createMatchedScenario(
            text: "珠海校区一起打羽毛球，4人",
            startDelay: 180,
            duration: 180
        )
        driveConfirmedGatheringThroughAction(scenario)
    }

    func testFlow5CourseDDLUsesProductionAssignmentCTA() {
        launchProduction("B4")
        tapButton("开一个 DDL 冲刺局", swipes: 10)
        XCTAssertTrue(any("screen-D1-intent").waitForExistence(timeout: 8))
        XCTAssertTrue(app.textViews["intent-text-input"].value as? String != "")
        driveCurrentIntentToPooling()
    }

    func testFlow6EventCompanionUsesProductionEventCTA() {
        launchProduction("B7")
        tapButton("找活动同行", swipes: 10)
        XCTAssertTrue(any("screen-D1-intent").waitForExistence(timeout: 8))
        XCTAssertTrue(app.textViews["intent-text-input"].value as? String != "")
        driveCurrentIntentToPooling()
    }

    func testFlow7ShareAcquisitionRestoresAfterLiveAuthenticationAndJoins() {
        let token = makeGapShareToken()
        launchDefault(extra: [
            "-ForceSignedOut", "YES",
            "-AutoCompleteLogin", "YES",
            "-LoginResumeUserID", "u_demo_1",
            "-ProductionDeepLink", "onemore://g/\(token)"
        ])
        XCTAssertTrue(any("screen-C4-share-landing").waitForExistence(timeout: 10))
        tapButton("认证后我来")
        XCTAssertTrue(any("screen-A2-auth-intro").waitForExistence(timeout: 5))
        tapButton("使用统一身份认证")
        tapButton("生成认证二维码")
        completeFirstUseIfPresented()
        XCTAssertTrue(app.buttons["我来"].waitForExistence(timeout: 20), "Share target was not restored")
        app.buttons["我来"].tap()
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 15))
    }

    func testFlow8GatheringRelationUsesFactOnlyProductionDetail() {
        let relationID = createCompletedRelationEvidence()
        launchDefault()
        app.tabBars.buttons["我"].tap()
        tapButton("搭子关系", swipes: 12)
        XCTAssertTrue(any("screen-E15-relations").waitForExistence(timeout: 10))
        XCTAssertTrue(app.buttons["再来一次"].firstMatch.waitForExistence(timeout: 6))
        XCTAssertTrue(app.buttons["进入对话"].firstMatch.waitForExistence(timeout: 6))
        let detail = app.buttons["relation-detail-\(relationID)"]
        for _ in 0..<12 where !detail.isHittable {
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(detail.waitForExistence(timeout: 5))
        XCTAssertTrue(detail.isHittable)
        detail.tap()
        let relationDetailScreen = any("screen-E16-relation-detail")
        for _ in 0..<3 where !relationDetailScreen.waitForExistence(timeout: 2) {
            // The first synthesized tap can be consumed immediately after the
            // long relation-list scroll. Move the row clear of the tab-bar hit
            // region, then re-query and retry; opening detail is idempotent.
            nudgeScroll(up: true)
            let retryDetail = app.buttons["relation-detail-\(relationID)"]
            for _ in 0..<4 where !retryDetail.isHittable {
                nudgeScroll(up: true)
            }
            XCTAssertTrue(retryDetail.waitForExistence(timeout: 2))
            XCTAssertTrue(retryDetail.isHittable)
            retryDetail.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        }
        XCTAssertTrue(relationDetailScreen.waitForExistence(timeout: 10))
        tapButton("解除关系（单方静默）…", swipes: 12)
        let confirmDissolution = app.alerts.buttons["确认解除"]
        for _ in 0..<3 where !confirmDissolution.waitForExistence(timeout: 2) {
            // A tab-bar overlay can occasionally consume the first synthesized
            // tap after a long ScrollView gesture. Move the control clear of the
            // overlay and retry; presenting confirmation performs no mutation.
            nudgeScroll(up: true)
            let dissolve = app.buttons["relation-dissolve-action"]
            XCTAssertTrue(dissolve.waitForExistence(timeout: 2))
            XCTAssertTrue(dissolve.isHittable)
            dissolve.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        }
        XCTAssertTrue(confirmDissolution.waitForExistence(timeout: 4))
        XCTAssertTrue(confirmDissolution.isHittable)
        confirmDissolution.tap()
        XCTAssertTrue(app.buttons["返回搭子关系"].waitForExistence(timeout: 12))
    }

    func testFlow9TrustCTAUsesProductionPublicGatherings() {
        launchDefault()
        app.tabBars.buttons["我"].tap()
        tapButton("信任进度", swipes: 10)
        XCTAssertTrue(any("screen-M3-trust").waitForExistence(timeout: 10))
        // 主路径：当前等级 + 下一级进度/权益；完整标准进升级说明，不再展示 capability 键墙。
        XCTAssertTrue(any("trust-current-level").waitForExistence(timeout: 8))
        let hasUpgrade = any("trust-upgrade-card").waitForExistence(timeout: 4)
        let atMax = any("trust-max-level").waitForExistence(timeout: 2)
        XCTAssertTrue(hasUpgrade || atMax, "Expected either upgrade progress or max-level card")
        XCTAssertTrue(any("trust-current-benefits").waitForExistence(timeout: 6))
        let openGuide = app.buttons["trust-open-guide"]
        for _ in 0..<10 where !openGuide.isHittable {
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(openGuide.waitForExistence(timeout: 6), "Missing upgrade guide CTA")
        openGuide.tap()
        XCTAssertTrue(any("sheet-trust-level-guide").waitForExistence(timeout: 8))
        for level in 0...4 {
            XCTAssertTrue(any("trust-guide-T\(level)").waitForExistence(timeout: 4), "Missing T\(level) guide entry")
        }
        if app.buttons["完成"].waitForExistence(timeout: 3) {
            app.buttons["完成"].tap()
        } else {
            app.swipeDown()
        }
        tapButton("查看信任申诉", swipes: 16)
        XCTAssertTrue(any("screen-M9-appeals").waitForExistence(timeout: 10))
        let reason = "UI 自动化复核本人的信任事实 \(UUID().uuidString.prefix(8))"
        let field = any("trust-appeal-reason")
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText(reason)
        tapButton("提交申诉", swipes: 8)
        XCTAssertTrue(app.staticTexts[reason].waitForExistence(timeout: 12))

        launchDefault()
        app.tabBars.buttons["我"].tap()
        tapButton("信任进度", swipes: 10)
        let publicGatheringsCTA = app.buttons["trust-open-low-risk-gatherings"]
        let usableBottom = app.frame.maxY - 150
        for _ in 0..<18 {
            if publicGatheringsCTA.exists,
               publicGatheringsCTA.frame.minY > 90,
               publicGatheringsCTA.frame.maxY < usableBottom {
                break
            }
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(publicGatheringsCTA.waitForExistence(timeout: 4), "M3 public gatherings CTA was not rendered")
        XCTAssertGreaterThan(publicGatheringsCTA.frame.minY, 90, "M3 public gatherings CTA is hidden under navigation chrome")
        XCTAssertLessThan(publicGatheringsCTA.frame.maxY, usableBottom, "M3 public gatherings CTA is hidden under the tab bar")
        publicGatheringsCTA.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        XCTAssertTrue(any("screen-C1-public-gatherings").waitForExistence(timeout: 10))
    }

    func testFlow9TrustGateCompletesLowRiskHistoryAndResumesOriginalTask() {
        let recoveringUser = createIsolatedTrustUser(role: "recover")
        let highCommitmentOwner = createIsolatedTrustUser(role: "highowner")
        let lowRiskOwner = createIsolatedTrustUser(role: "owner")
        let lowRiskPeer = createIsolatedTrustUser(role: "peer")
        let highCommitmentID = createHighCommitmentGathering(ownerID: highCommitmentOwner)

        launchDefault(
            userID: recoveringUser,
            extra: ["-ProductionDeepLink", "onemore://gathering/\(highCommitmentID)"]
        )
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 12))
        tapButton("加入这个局", swipes: 12)

        XCTAssertTrue(
            any("screen-C3-trust-requirement").waitForExistence(timeout: 12),
            "A real T1 rejection did not route to C3"
        )
        XCTAssertTrue(any("trust-current-level").waitForExistence(timeout: 8))
        XCTAssertTrue(any("trust-required-level").waitForExistence(timeout: 8))
        XCTAssertTrue(any("trust-current-level").label.contains("T1"))
        XCTAssertTrue(any("trust-required-level").label.contains("T2"))
        XCTAssertTrue(
            app.staticTexts.matching(
                NSPredicate(format: "label CONTAINS %@", "双人高承诺局")
            ).firstMatch.exists
        )

        let firstLowRisk = createLowRiskPool(
            ownerID: lowRiskOwner,
            startDelay: 14,
            duration: 1
        )
        tapButton("去参加低风险公开局", swipes: 12)
        XCTAssertTrue(any("screen-C1-public-gatherings").waitForExistence(timeout: 12))
        let firstPoolButton = app.buttons.matching(
            NSPredicate(format: "label CONTAINS %@", firstLowRisk.titleToken)
        ).firstMatch
        for _ in 0..<20 where !firstPoolButton.isHittable {
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(firstPoolButton.waitForExistence(timeout: 5), "Low-risk pool was not rendered")
        XCTAssertTrue(firstPoolButton.isHittable, "Low-risk pool was not reachable")
        firstPoolButton.tap()
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 10))
        tapButton("加入这个局", swipes: 12)

        _ = apiData(
            "/gatherings/\(firstLowRisk.id)/join",
            method: "POST",
            userID: lowRiskPeer,
            body: [:]
        )
        finishLowRiskGathering(
            firstLowRisk.id,
            endAt: firstLowRisk.endAt,
            members: [recoveringUser, lowRiskOwner, lowRiskPeer]
        )

        for _ in 0..<2 {
            let lowRisk = createLowRiskPool(
                ownerID: lowRiskOwner,
                startDelay: 2.5,
                duration: 1
            )
            _ = apiData(
                "/gatherings/\(lowRisk.id)/join",
                method: "POST",
                userID: recoveringUser,
                body: [:]
            )
            _ = apiData(
                "/gatherings/\(lowRisk.id)/join",
                method: "POST",
                userID: lowRiskPeer,
                body: [:]
            )
            finishLowRiskGathering(
                lowRisk.id,
                endAt: lowRisk.endAt,
                members: [recoveringUser, lowRiskOwner, lowRiskPeer]
            )
        }

        let progress = apiData("/trust/me", userID: recoveringUser) as! [String: Any]
        XCTAssertEqual(progress["level"] as? String, "T2")
        let statistics = progress["statistics"] as! [String: Any]
        XCTAssertEqual(statistics["completed_gatherings"] as? Int, 3)

        let detailBack = app.navigationBars.buttons.firstMatch
        XCTAssertTrue(detailBack.waitForExistence(timeout: 5))
        detailBack.tap()
        XCTAssertTrue(any("screen-C1-public-gatherings").waitForExistence(timeout: 8))
        let listBack = app.navigationBars.buttons.firstMatch
        XCTAssertTrue(listBack.waitForExistence(timeout: 5))
        listBack.tap()
        XCTAssertTrue(any("screen-C3-trust-requirement").waitForExistence(timeout: 8))

        tapButton("刷新信任进度", swipes: 12)
        XCTAssertTrue(
            app.buttons["继续加入原来的局"].waitForExistence(timeout: 12),
            "C3 did not expose the preserved task after the server promoted T2"
        )
        tapButton("继续加入原来的局", swipes: 12)
        XCTAssertTrue(any("screen-E3-gathering-detail").waitForExistence(timeout: 12))
        tapButton("加入这个局", swipes: 12)
        XCTAssertTrue(
            app.staticTexts["分别确认"].waitForExistence(timeout: 12),
            "The original high-commitment task did not resume after T2"
        )
    }

    func testOrganizerFlowAndTasteImportEntry() {
        _ = apiData(
            "/internal/trust/u_demo_1/organizer-verification",
            method: "POST",
            body: ["verified": true],
            extraHeaders: ["X-Admin-Token": "change-me"]
        )
        launchDefault()
        app.tabBars.buttons["我"].tap()
        tapButton("主理人控制台", swipes: 14)
        XCTAssertTrue(any("screen-O1-organizer").waitForExistence(timeout: 10))
        tapButton("直接创建官方局", swipes: 8)
        XCTAssertTrue(any("screen-O2-create-official").waitForExistence(timeout: 5))
        app.buttons["取消"].tap()
        XCTAssertTrue(any("screen-O4-templates").waitForExistence(timeout: 5))

        launchDefault()
        app.tabBars.buttons["我"].tap()
        let tasteEntry = app.buttons["profile-taste-import"]
        let usableBottom = app.frame.maxY - 150
        for _ in 0..<18 {
            if tasteEntry.exists,
               tasteEntry.frame.minY > 90,
               tasteEntry.frame.maxY < usableBottom {
                break
            }
            app.swipeUp()
            Thread.sleep(forTimeInterval: 0.08)
        }
        XCTAssertTrue(tasteEntry.waitForExistence(timeout: 5))
        XCTAssertGreaterThan(tasteEntry.frame.minY, 90)
        XCTAssertLessThan(tasteEntry.frame.maxY, usableBottom)
        tasteEntry.coordinate(withNormalizedOffset: CGVector(dx: 0.5, dy: 0.5)).tap()
        let tasteHeader = app.descendants(matching: .any)
            .matching(NSPredicate(format: "label CONTAINS %@", "导入兴趣画像"))
            .firstMatch
        XCTAssertTrue(tasteHeader.waitForExistence(timeout: 5))
    }

    func testNamedCTAProducesVisibleBehaviorInsteadOfDeadTap() {
        launchDefault()
        let entry = any("today-hermes-entry")
        XCTAssertTrue(entry.waitForExistence(timeout: 6))
        entry.tap()
        XCTAssertTrue(any("screen-B2-hermes").waitForExistence(timeout: 6))
    }
}
