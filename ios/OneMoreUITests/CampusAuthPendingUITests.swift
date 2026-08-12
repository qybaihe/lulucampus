import XCTest

/// Visual smoke: PENDING shows loading slot; auth surface fills screen width.
final class CampusAuthPendingUITests: XCTestCase {
    func testPendingShowsLoadingNotFakeQR() throws {
        let app = XCUIApplication()
        app.terminate()
        app.launchArguments = [
            "-UIAccessibilityReduceMotionEnabled", "YES",
            "-ProductionDeepLink", "onemore://auth",
        ]
        app.launch()

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for label in ["允许完全访问", "允许", "Allow Full Access", "Allow"] {
            let button = springboard.buttons[label].firstMatch
            if button.waitForExistence(timeout: 0.8) { button.tap() }
        }

        // Finish first-use if keychain session still authenticates.
        if app.descendants(matching: .any)["first-use-save-grants"].waitForExistence(timeout: 3) {
            app.descendants(matching: .any)["first-use-save-grants"].tap()
            if app.descendants(matching: .any)["first-use-confirm-facts"].waitForExistence(timeout: 8) {
                app.descendants(matching: .any)["first-use-confirm-facts"].tap()
            }
            if app.descendants(matching: .any)["first-use-skip-social"].waitForExistence(timeout: 6) {
                app.descendants(matching: .any)["first-use-skip-social"].tap()
            }
            if app.descendants(matching: .any)["first-use-finish"].waitForExistence(timeout: 6) {
                app.descendants(matching: .any)["first-use-finish"].tap()
            }
        }

        // Prefer landing on campus gate via deep link + sysu prefs; otherwise drive UI.
        if !app.descendants(matching: .any)["screen-A3-real-login"].waitForExistence(timeout: 3) {
            if app.tabBars.buttons["我"].waitForExistence(timeout: 4) {
                app.tabBars.buttons["我"].tap()
            }
            let sysu = app.descendants(matching: .any)["auth-school-sysu"]
            if sysu.waitForExistence(timeout: 3) {
                sysu.tap()
            } else {
                let labeled = app.staticTexts["中山大学"]
                if labeled.waitForExistence(timeout: 2) {
                    app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "中山大学")).firstMatch.tap()
                }
            }
        }

        XCTAssertTrue(
            app.descendants(matching: .any)["screen-A3-real-login"].waitForExistence(timeout: 8),
            "campus auth screen missing"
        )

        let auth = app.descendants(matching: .any)["screen-A3-real-login"].firstMatch
        let width = auth.frame.width
        XCTAssertGreaterThan(width, 350, "auth surface still looks like a narrow strip: \(width)")

        if app.descendants(matching: .any)["auth-start-button"].waitForExistence(timeout: 4) {
            app.descendants(matching: .any)["auth-start-button"].tap()
        } else {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "生成")).firstMatch.tap()
        }

        XCTAssertTrue(
            app.descendants(matching: .any)["campus-auth-qr-loading"].waitForExistence(timeout: 10),
            "PENDING should show loading slot"
        )
        XCTAssertFalse(app.staticTexts["PENDING"].waitForExistence(timeout: 1))

        let shot = app.screenshot()
        let out = URL(fileURLWithPath: "/Users/baihe/Documents/compusone/ios/artifacts/hermes-verify/05-campus-auth-pending.png")
        try? FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? shot.pngRepresentation.write(to: out)
        add(XCTAttachment(screenshot: shot))
    }
}
