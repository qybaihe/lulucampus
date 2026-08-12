import XCTest

/// 截图专用：以测试账号 u_demo_1 深链进入「抖音兴趣画像」，
/// 后端已用 scripts/seed_demo_taste_profile.py 写入演示画像，
/// 捕获画像卡（taste-profile-result）全屏截图。
final class TastePersonaScreenshotTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    func testTastePersonaCardScreenshot() throws {
        app.launchArguments = [
            "-UI_TESTING", "YES",
            "-DevUserIDOverride", "u_demo_1",
            "-UIAccessibilityReduceMotionEnabled", "YES",
            "-ProductionDeepLink", "onemore://taste-import",
        ]
        app.launch()

        let card = app.descendants(matching: .any)["taste-profile-result"]
        XCTAssertTrue(card.waitForExistence(timeout: 15), "画像卡未出现（确认后端 127.0.0.1:8000 已启动且已 seed 演示画像）")

        // 等画像数据与 Lulu 动效稳定
        sleep(2)

        let fullPage = app.screenshot()
        let fullAttachment = XCTAttachment(screenshot: fullPage)
        fullAttachment.name = "taste-persona-card-full"
        fullAttachment.lifetime = .keepAlways
        add(fullAttachment)

        // 滚一屏再截一张，覆盖卡片下半部分
        app.swipeUp()
        sleep(1)
        let scrolled = app.screenshot()
        let scrolledAttachment = XCTAttachment(screenshot: scrolled)
        scrolledAttachment.name = "taste-persona-card-scrolled"
        scrolledAttachment.lifetime = .keepAlways
        add(scrolledAttachment)
    }
}
