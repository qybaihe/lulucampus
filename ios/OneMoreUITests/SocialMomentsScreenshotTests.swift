import XCTest

/// 社交层截图取证：依赖 127.0.0.1:8000 后端与 scripts/seed_social_demo.py 演示数据。
/// 运行方式（按需注入局/关系 ID）：
///   SOCIAL_POOLING_ID=… SOCIAL_TENTATIVE_ID=… SOCIAL_RELATION_ID=… ./Scripts/test.sh
/// 截图直接写入宿主机 ios/artifacts/screenshots/social/。
final class SocialMomentsScreenshotTests: XCTestCase {
    private var app: XCUIApplication!

    private static let outputDirectory = URL(
        fileURLWithPath: "/Users/baihe/Documents/compusone/artifacts/screenshots/social",
        isDirectory: true
    )

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
        try? FileManager.default.createDirectory(
            at: Self.outputDirectory, withIntermediateDirectories: true
        )
    }

    private func launch(deepLink: String? = nil, reduceMotion: Bool = true) {
        var arguments = [
            "-UI_TESTING", "YES",
            "-DevUserIDOverride", "u_demo_1",
        ]
        if reduceMotion {
            arguments += ["-UIAccessibilityReduceMotionEnabled", "YES"]
        }
        if let deepLink {
            arguments += ["-ProductionDeepLink", deepLink]
        }
        app.launchArguments = arguments
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

    private func env(_ key: String) -> String? {
        let value = ProcessInfo.processInfo.environment[key]
        return (value?.isEmpty ?? true) ? nil : value
    }

    /// 1 · 意图卡：一句话心情输入。
    func testIntentComposerMoodNote() throws {
        launch(deepLink: "onemore://intent")
        let field = app.descendants(matching: .any)["intent-mood-note-input"]
        XCTAssertTrue(field.waitForExistence(timeout: 15), "心情输入框未出现")
        field.tap()
        field.typeText("考完试想出出汗，来个不咕的")
        app.swipeDown()
        sleep(1)
        snap("01-intent-mood-note")
    }

    /// 2 · 等待期：噜噜寻人陪伴 + 座位点。
    func testPoolWaitingCompanion() throws {
        guard let gatheringID = env("SOCIAL_POOLING_ID") else {
            throw XCTSkip("未注入 SOCIAL_POOLING_ID")
        }
        launch(deepLink: "onemore://gathering/\(gatheringID)")
        let waiting = app.descendants(matching: .any)["gathering-pool-waiting"]
        XCTAssertTrue(waiting.waitForExistence(timeout: 15), "等待陪伴卡未出现")
        sleep(2)
        snap("02-pool-waiting-lulu")
    }

    /// 3 · 缺口卡：还差 N 人 + 心情 + 分享链接。
    func testGapShareCard() throws {
        guard let gatheringID = env("SOCIAL_POOLING_ID") else {
            throw XCTSkip("未注入 SOCIAL_POOLING_ID")
        }
        launch(deepLink: "onemore://gathering/\(gatheringID)")
        let create = app.descendants(matching: .any)["gathering-create-share"]
        if create.waitForExistence(timeout: 10) {
            create.tap()
        }
        let share = app.descendants(matching: .any)["gathering-share-link"]
        XCTAssertTrue(share.waitForExistence(timeout: 15), "缺口卡未出现")
        share.firstMatch.scrollToVisible()
        sleep(1)
        snap("03-gap-share-card")
    }

    /// 4 · 座满仪式：最后一人确认 → 全屏庆祝（关掉 Reduce Motion 拍动画结束帧）。
    func testCelebrationOverlay() throws {
        guard let gatheringID = env("SOCIAL_TENTATIVE_ID") else {
            throw XCTSkip("未注入 SOCIAL_TENTATIVE_ID")
        }
        launch(deepLink: "onemore://gathering/\(gatheringID)", reduceMotion: false)
        let confirm = app.buttons["确认参加"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 15), "确认按钮未出现")
        confirm.tap()
        let overlay = app.descendants(matching: .any)["gathering-celebration-overlay"]
        XCTAssertTrue(overlay.waitForExistence(timeout: 20), "座满仪式未触发")
        sleep(3)
        snap("04-celebration-overlay")
        let enter = app.buttons["看看为什么是你们"]
        if enter.waitForExistence(timeout: 5) {
            enter.tap()
        }
        let icebreaker = app.descendants(matching: .any)["gathering-icebreaker-card"]
        XCTAssertTrue(icebreaker.waitForExistence(timeout: 15), "破冰卡未出现")
        sleep(1)
        snap("05-icebreaker-card")
    }

    /// 6 · 群聊：系统成局卡首条消息。
    func testChannelSystemCard() throws {
        guard let channelID = env("SOCIAL_CHANNEL_ID") else {
            throw XCTSkip("未注入 SOCIAL_CHANNEL_ID")
        }
        launch(deepLink: "onemore://channel/\(channelID)")
        let card = app.descendants(matching: .any)["channel-system-gathering-card"]
        XCTAssertTrue(card.waitForExistence(timeout: 15), "系统成局卡未出现")
        sleep(1)
        snap("06-channel-system-card")
    }

    /// 7 · 搭子档案：称号 + 里程碑 + 时间线。
    func testRelationProfile() throws {
        guard let relationID = env("SOCIAL_RELATION_ID") else {
            throw XCTSkip("未注入 SOCIAL_RELATION_ID")
        }
        launch(deepLink: "onemore://relation/\(relationID)")
        let recur = app.descendants(matching: .any)["relation-detail-recur"]
        XCTAssertTrue(recur.waitForExistence(timeout: 15), "档案页未加载")
        sleep(1)
        snap("07-relation-profile")
    }

    /// 10 · 复局满屏三选一。
    func testRecurrenceChoice() throws {
        guard let gatheringID = env("SOCIAL_COMPLETED_ID") else {
            throw XCTSkip("未注入 SOCIAL_COMPLETED_ID")
        }
        launch(deepLink: "onemore://gathering/\(gatheringID)")
        let recur = app.buttons["再来一次"]
        XCTAssertTrue(recur.waitForExistence(timeout: 15), "复局入口未出现")
        recur.scrollToVisible()
        recur.tap()
        let option = app.descendants(matching: .any)["screen-E10-recurrence-choice"]
        XCTAssertTrue(option.waitForExistence(timeout: 10), "复局三选一未打开")
        sleep(1)
        snap("10-recurrence-choice")
    }

    /// 8 · 信任解锁叙事。
    func testTrustNarrative() throws {
        launch(deepLink: "onemore://trust")
        let card = app.descendants(matching: .any)["trust-upgrade-card"]
        XCTAssertTrue(card.waitForExistence(timeout: 15), "升级进度卡未出现")
        sleep(1)
        snap("08-trust-narrative")
    }

    /// 9 · 学期回忆录。
    func testSemesterRecap() throws {
        app.launchArguments = [
            "-UI_TESTING", "YES",
            "-DevUserIDOverride", "u_demo_1",
            "-UIAccessibilityReduceMotionEnabled", "YES",
            "-InitialTab", "profile",
        ]
        app.launch()
        let entry = app.descendants(matching: .any)["profile-semester-recap-entry"]
        XCTAssertTrue(entry.waitForExistence(timeout: 10), "回忆录入口未出现")
        entry.tap()
        let sheet = app.descendants(matching: .any)["profile-semester-recap"]
        XCTAssertTrue(sheet.waitForExistence(timeout: 15), "回忆录未打开")
        sleep(2)
        snap("09-semester-recap")
    }
}

private extension XCUIElement {
    /// 将元素滚动进可视区（简化版：最多上滑 4 屏）。
    func scrollToVisible() {
        var attempts = 0
        while !isHittable, attempts < 4 {
            XCUIApplication().swipeUp()
            attempts += 1
        }
    }
}
