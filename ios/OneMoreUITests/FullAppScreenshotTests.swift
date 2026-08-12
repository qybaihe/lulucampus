import XCTest

/// 全 App 高清截图取证：文档配图用。
///
/// 前置：
/// 1. 后端运行在 127.0.0.1:8000
/// 2. `python scripts/seed_screenshot_tour.py > artifacts/screenshot-tour-ids.json`
///
/// 截图（模拟器原生 3x 分辨率 PNG）输出到 artifacts/screenshots/full/。
final class FullAppScreenshotTests: XCTestCase {
    private var app: XCUIApplication!

    private static let outputDirectory = URL(
        fileURLWithPath: "/Users/baihe/Documents/compusone/artifacts/screenshots/full",
        isDirectory: true
    )

    /// seed 脚本产出的演示数据 ID。
    private static let ids: [String: String] = {
        let url = URL(fileURLWithPath: "/Users/baihe/Documents/compusone/artifacts/screenshot-tour-ids.json")
        guard let data = try? Data(contentsOf: url),
              let raw = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
        return raw.compactMapValues { $0 as? String }
    }()

    override func setUp() {
        continueAfterFailure = false
        try? FileManager.default.createDirectory(
            at: Self.outputDirectory, withIntermediateDirectories: true
        )
    }

    // MARK: - 基建

    private func launch(deepLink: String? = nil, tab: String? = nil, reduceMotion: Bool = true) {
        app = XCUIApplication()
        var args = ["-UI_TESTING", "YES", "-DevUserIDOverride", "u_demo_1"]
        if reduceMotion { args += ["-UIAccessibilityReduceMotionEnabled", "YES"] }
        if let tab { args += ["-InitialTab", tab] }
        if let deepLink { args += ["-ProductionDeepLink", deepLink] }
        app.launchArguments = args
        app.launch()
    }

    private func snap(_ name: String) {
        let image = app.screenshot().pngRepresentation
        let url = Self.outputDirectory.appendingPathComponent("\(name).png")
        try? image.write(to: url)
        let attachment = XCTAttachment(uniformTypeIdentifier: "public.png", name: name, payload: image)
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    private func settle(_ seconds: UInt32 = 3) { sleep(seconds) }

    private func requireID(_ key: String) throws -> String {
        guard let value = Self.ids[key], !value.isEmpty else {
            throw XCTSkip("screenshot-tour-ids.json 缺少 \(key)")
        }
        return value
    }

    /// 点掉系统权限弹窗（如通知授权），避免遮挡截图与按钮。
    private func dismissSystemAlertIfNeeded() {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for label in ["允许完全访问", "允许", "Allow Full Access", "Allow"] {
            let button = springboard.buttons[label].firstMatch
            if button.waitForExistence(timeout: 2) {
                button.tap()
                return
            }
        }
    }

    // MARK: - 五个 Tab 根

    func test01TabToday() throws {
        launch(tab: "today")
        settle(5)
        snap("01-tab-today")
    }

    func test02TabActivities() throws {
        launch(tab: "competitions")
        settle(5)
        snap("02-tab-activities")
    }

    func test03TabIntentComposer() throws {
        launch(tab: "create")
        settle(3)
        snap("03-tab-intent-composer")
    }

    func test04TabMessages() throws {
        launch(tab: "messages")
        settle(4)
        snap("04-tab-messages")
    }

    func test05TabProfile() throws {
        launch(tab: "profile")
        settle(4)
        snap("05-tab-profile")
    }

    // MARK: - 校园工具

    func test06HermesAsk() throws {
        launch(deepLink: "onemore://screen/B2")
        settle(3)
        snap("06-hermes-ask")
    }

    func test07Timetable() throws {
        launch(deepLink: "onemore://screen/B3")
        dismissSystemAlertIfNeeded()
        settle(6)
        snap("07-timetable")
    }

    /// 日程 3 天窗口左滑翻页后的状态。
    func test07bTimetableSwiped() throws {
        launch(deepLink: "onemore://screen/B3")
        dismissSystemAlertIfNeeded()
        settle(6)
        app.swipeLeft()
        settle(2)
        snap("07b-timetable-swiped")
    }

    func test08Assignments() throws {
        launch(deepLink: "onemore://screen/B4")
        settle(6)
        snap("08-assignments")
    }

    func test09GymVenues() throws {
        launch(deepLink: "onemore://screen/B5")
        settle(15)
        snap("09-gym-venues")
    }

    func test10StudyRooms() throws {
        launch(deepLink: "onemore://screen/B6")
        settle(15)
        snap("10-study-rooms")
    }

    func test11CampusEvents() throws {
        launch(deepLink: "onemore://screen/B7")
        settle(6)
        snap("11-campus-events")
    }

    func test12ResearchQuery() throws {
        launch(deepLink: "onemore://screen/B8")
        settle(15)
        snap("12-research-query")
    }

    func test13Transit() throws {
        launch(deepLink: "onemore://screen/B9")
        settle(4)
        snap("13-transit")
    }

    // MARK: - 意图与发现

    /// D1 输入 → D3 意图卡编辑器（真实走一遍 Lulu 理解编译）。
    func test14IntentCompile() throws {
        launch(tab: "create")
        let input = app.descendants(matching: .any)["intent-text-input"].firstMatch
        let editorArrives = app.descendants(matching: .any)["screen-D3-intent-editor"]
        if input.waitForExistence(timeout: 8) {
            input.tap()
            input.typeText("周日下午想约三个人打两小时羽毛球")
        }
        let compile = app.descendants(matching: .any)["intent-compile-button"].firstMatch
        if compile.waitForExistence(timeout: 4) {
            compile.tap()
        }
        _ = editorArrives.waitForExistence(timeout: 20)
        // 收起键盘，露出意图卡摘要。
        let done = app.toolbars.buttons["完成"].firstMatch
        if done.exists { done.tap() } else { app.swipeDown() }
        settle(1)
        snap("14-intent-card-editor")

        let toggle = app.descendants(matching: .any)["intent-fine-tune-toggle"].firstMatch
        if toggle.waitForExistence(timeout: 4) {
            toggle.scrollToVisible()
            toggle.tap()
            settle(1)
            app.swipeUp()
            settle(1)
            snap("14b-intent-fine-tune")
        }
    }

    func test15PublicGatherings() throws {
        launch(deepLink: "onemore://public-gatherings")
        settle(5)
        snap("15-public-gatherings")
    }

    func test16MyGatherings() throws {
        launch(deepLink: "onemore://my-gatherings")
        settle(5)
        snap("16-my-gatherings")
    }

    // MARK: - 局生命周期

    /// Pooling：噜噜寻人陪伴 + 座位点 + 缺口分享卡。
    func test17PoolingAndGapShare() throws {
        let id = try requireID("pooling_id")
        launch(deepLink: "onemore://gathering/\(id)")
        let waiting = app.descendants(matching: .any)["gathering-pool-waiting"]
        _ = waiting.waitForExistence(timeout: 12)
        settle(2)
        snap("17-gathering-pooling")

        let create = app.descendants(matching: .any)["gathering-create-share"]
        if create.waitForExistence(timeout: 6) {
            create.tap()
        }
        let share = app.descendants(matching: .any)["gathering-share-link"]
        _ = share.waitForExistence(timeout: 12)
        share.firstMatch.scrollToVisible()
        settle(1)
        snap("18-gap-share-card")
    }

    /// Tentative 确认页 → 座满仪式（动画两帧）→ 破冰卡。
    func test19TentativeToCelebration() throws {
        let id = try requireID("tentative_id")
        launch(deepLink: "onemore://gathering/\(id)", reduceMotion: false)
        let confirm = app.buttons["确认参加"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 12), "确认按钮未出现")
        dismissSystemAlertIfNeeded()
        settle(1)
        snap("19-gathering-tentative-confirm")

        confirm.tap()
        let overlay = app.descendants(matching: .any)["gathering-celebration-overlay"]
        XCTAssertTrue(overlay.waitForExistence(timeout: 15), "座满仪式未触发")
        usleep(1_200_000)
        snap("20-celebration-moment")

        let enter = app.buttons["看看为什么是你们"]
        _ = enter.waitForExistence(timeout: 8)
        usleep(600_000)
        snap("21-celebration-full")

        if enter.exists { enter.tap() }
        let icebreaker = app.descendants(matching: .any)["gathering-icebreaker-card"]
        _ = icebreaker.waitForExistence(timeout: 12)
        settle(2)
        snap("22-icebreaker-card")
    }

    /// Confirmed 局详情（协作空间）。
    func test23ConfirmedGathering() throws {
        let id = try requireID("confirmed_id")
        launch(deepLink: "onemore://gathering/\(id)")
        settle(5)
        snap("23-gathering-confirmed")
    }

    /// 群聊：系统成局卡 + Lulu 开场白。
    func test24ChannelSystemCard() throws {
        let id = try requireID("channel_id")
        launch(deepLink: "onemore://channel/\(id)")
        let card = app.descendants(matching: .any)["channel-system-gathering-card"]
        _ = card.waitForExistence(timeout: 12)
        settle(2)
        snap("24-channel-system-card")
    }

    /// Completed 局 → 复局满屏三选一。
    func test25CompletedAndRecurrence() throws {
        let id = try requireID("completed_id")
        launch(deepLink: "onemore://gathering/\(id)")
        settle(4)
        snap("25-gathering-completed")

        let recur = app.buttons["再来一次"]
        if recur.waitForExistence(timeout: 8) {
            recur.scrollToVisible()
            recur.tap()
            let choice = app.descendants(matching: .any)["screen-E10-recurrence-choice"]
            _ = choice.waitForExistence(timeout: 8)
            settle(1)
            snap("26-recurrence-choice")
        }
    }

    // MARK: - 关系与信任

    func test27RelationsList() throws {
        launch(deepLink: "onemore://relations")
        settle(5)
        snap("27-relations-list")
    }

    func test28RelationProfile() throws {
        let id = try requireID("relation_id")
        launch(deepLink: "onemore://relation/\(id)")
        settle(5)
        snap("28-relation-profile")
    }

    func test29SharedGoals() throws {
        let id = try requireID("relation_id")
        launch(deepLink: "onemore://goal/\(id)")
        settle(5)
        snap("29-shared-goals")
    }

    func test30TrustProgress() throws {
        launch(deepLink: "onemore://trust")
        settle(5)
        snap("30-trust-progress")
    }

    /// 学期回忆录（Wrapped 式聚合）。
    func test31SemesterRecap() throws {
        launch(tab: "profile")
        let entry = app.descendants(matching: .any)["profile-semester-recap-entry"]
        XCTAssertTrue(entry.waitForExistence(timeout: 10), "回忆录入口未出现")
        entry.tap()
        let sheet = app.descendants(matching: .any)["profile-semester-recap"]
        _ = sheet.waitForExistence(timeout: 12)
        settle(3)
        snap("31-semester-recap")
    }

    // MARK: - 我的 · 设置面

    func test32ProfileEditor() throws {
        launch(deepLink: "onemore://screen/M2")
        settle(5)
        snap("32-profile-editor")
    }

    func test33Privacy() throws {
        launch(deepLink: "onemore://screen/M5")
        settle(4)
        snap("33-privacy-settings")
    }

    func test34MatchingPreferences() throws {
        launch(deepLink: "onemore://matching-preferences")
        settle(4)
        snap("34-matching-preferences")
    }

    func test35Notifications() throws {
        launch(deepLink: "onemore://screen/M7")
        settle(4)
        snap("35-notification-settings")
    }

    func test36Blocks() throws {
        launch(deepLink: "onemore://blocks")
        settle(4)
        snap("36-block-list")
    }

    func test37Appeals() throws {
        launch(deepLink: "onemore://screen/M9")
        settle(4)
        snap("37-trust-appeals")
    }

    func test38Grants() throws {
        launch(deepLink: "onemore://grants")
        settle(4)
        snap("38-grant-management")
    }

    func test39AccountData() throws {
        launch(deepLink: "onemore://account-data")
        settle(4)
        snap("39-account-data")
    }

    func test40TasteImport() throws {
        launch(deepLink: "onemore://taste-import")
        settle(5)
        snap("40-taste-import")
    }

    func test41Organizer() throws {
        launch(deepLink: "onemore://organizer")
        settle(5)
        snap("41-organizer-console")
    }

    func test42CompetitionDetail() throws {
        let id = try requireID("competition_id")
        launch(deepLink: "onemore://competition/\(id)")
        settle(5)
        snap("42-competition-detail")
    }

    func test43Diagnostics() throws {
        launch(deepLink: "onemore://diagnostics")
        settle(4)
        snap("43-diagnostics")
    }

    func test44SafetyHistory() throws {
        launch(deepLink: "onemore://safety-history")
        settle(4)
        snap("44-safety-history")
    }
}

private extension XCUIElement {
    /// 将元素滚动进可视区（最多上滑 4 屏）。
    func scrollToVisible() {
        var attempts = 0
        while !isHittable, attempts < 4 {
            XCUIApplication().swipeUp()
            attempts += 1
        }
    }
}
