import XCTest

/// Visual smoke: PENDING shows loading slot; auth surface fills screen width.
final class CampusAuthPendingUITests: XCTestCase {
    func testPendingShowsLoadingNotFakeQR() throws {
        let app = XCUIApplication()
        app.terminate()
        app.launchArguments = [
            "-UIAccessibilityReduceMotionEnabled", "YES",
            // Force guest + SYSU campus gate without relying on residual prefs.
            "-com.onemore.campus.auth.session-expired", "YES",
            "-onemore.school.affiliation.v1", "sysu",
            "-onemore.school.campusGate.v1", "NO",
            "-ProductionDeepLink", "onemore://auth",
        ]
        app.launch()

        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for label in ["允许完全访问", "允许", "Allow Full Access", "Allow"] {
            let button = springboard.buttons[label].firstMatch
            if button.waitForExistence(timeout: 0.8) { button.tap() }
        }

        let a3 = app.descendants(matching: .any)["screen-A3-real-login"]
        if !a3.waitForExistence(timeout: 6) {
            if app.tabBars.buttons["我"].waitForExistence(timeout: 4) {
                app.tabBars.buttons["我"].tap()
            }
            XCTAssertTrue(a3.waitForExistence(timeout: 8), "campus auth screen missing")
        }

        let width = a3.firstMatch.frame.width
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

        // Give pulse animation a beat, then capture.
        Thread.sleep(forTimeInterval: 0.8)
        let shot = app.screenshot()
        let out = URL(fileURLWithPath: "/Users/baihe/Documents/compusone/ios/artifacts/hermes-verify/05-campus-auth-pending.png")
        try? FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? shot.pngRepresentation.write(to: out)
        add(XCTAttachment(screenshot: shot))
    }
}
