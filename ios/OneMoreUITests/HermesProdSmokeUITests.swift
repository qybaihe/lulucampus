import XCTest

/// Production Hermes smoke: phone login against live API, then ask today's courses.
final class HermesProdSmokeUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() {
        continueAfterFailure = false
        app = XCUIApplication()
    }

    private func any(_ identifier: String) -> XCUIElement {
        app.descendants(matching: .any)[identifier]
    }

    private func dismissSystemAlertIfNeeded() {
        let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        for label in ["允许完全访问", "允许", "Allow Full Access", "Allow", "以后"] {
            let button = springboard.buttons[label].firstMatch
            if button.waitForExistence(timeout: 1.0) {
                button.tap()
            }
        }
    }

    private func tapTab(_ title: String) {
        let tab = app.tabBars.buttons[title]
        XCTAssertTrue(tab.waitForExistence(timeout: 12), "missing tab \(title)")
        tab.tap()
    }

    private func finishFirstUseIfNeeded() {
        guard any("screen-A4-grants").waitForExistence(timeout: 3)
            || any("first-use-save-grants").waitForExistence(timeout: 1) else { return }

        if any("first-use-save-grants").waitForExistence(timeout: 3) {
            any("first-use-save-grants").tap()
        } else {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "保存授权")).firstMatch.tap()
        }
        if any("first-use-confirm-facts").waitForExistence(timeout: 10) {
            any("first-use-confirm-facts").tap()
        } else if app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "无误")).firstMatch.waitForExistence(timeout: 4) {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "无误")).firstMatch.tap()
        }
        if any("first-use-skip-social").waitForExistence(timeout: 8) {
            any("first-use-skip-social").tap()
        } else if any("first-use-enable-social").waitForExistence(timeout: 2) {
            any("first-use-enable-social").tap()
        } else if app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "跳过")).firstMatch.waitForExistence(timeout: 2) {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "跳过")).firstMatch.tap()
        }
        if any("first-use-skip-taste").waitForExistence(timeout: 8) {
            any("first-use-skip-taste").tap()
        } else if any("first-use-taste-continue").waitForExistence(timeout: 2) {
            any("first-use-taste-continue").tap()
        } else if app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "稍后再贴")).firstMatch.waitForExistence(timeout: 2) {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "稍后再贴")).firstMatch.tap()
        }
        if any("first-use-finish").waitForExistence(timeout: 8) {
            any("first-use-finish").tap()
        } else if app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "进入今天")).firstMatch.waitForExistence(timeout: 4) {
            app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "进入今天")).firstMatch.tap()
        }
    }

    private func ensureLoggedInWithPhone() {
        // Keychain may survive uninstall; FirstUse can appear without tabs.
        finishFirstUseIfNeeded()
        if any("screen-B1-today").waitForExistence(timeout: 3) {
            return
        }
        if app.tabBars.buttons["今天"].waitForExistence(timeout: 3),
           !app.staticTexts["访客模式"].waitForExistence(timeout: 1) {
            // Authenticated tabs already available.
            return
        }

        // Guest → open auth via profile tab, or auth already visible.
        if app.tabBars.buttons["我"].waitForExistence(timeout: 4) {
            app.tabBars.buttons["我"].tap()
        }

        XCTAssertTrue(any("screen-A2-auth-intro").waitForExistence(timeout: 8)
            || any("screen-A2b-phone-auth").waitForExistence(timeout: 2)
            || app.staticTexts["你在哪所学校？"].waitForExistence(timeout: 2),
            "auth flow missing")

        if app.staticTexts["你在哪所学校？"].waitForExistence(timeout: 3)
            || any("auth-school-other").waitForExistence(timeout: 1) {
            if any("auth-school-other").waitForExistence(timeout: 2) {
                any("auth-school-other").tap()
            } else {
                app.buttons.containing(NSPredicate(format: "label CONTAINS %@", "其他")).firstMatch.tap()
            }
        } else if app.staticTexts["先用企业微信扫码完成校园核验，下一步再用手机号登录"].waitForExistence(timeout: 2) {
            XCTFail("stuck on SYSU campus QR gate")
        }

        XCTAssertTrue(
            any("screen-A2b-phone-auth").waitForExistence(timeout: 10)
                || app.staticTexts["欢迎回来"].waitForExistence(timeout: 2),
            "phone auth not shown"
        )

        let phoneField = any("phone-auth-phone").firstMatch
        if phoneField.waitForExistence(timeout: 4) {
            phoneField.tap()
            phoneField.typeText("13800138000")
            any("phone-auth-password").firstMatch.tap()
            any("phone-auth-password").firstMatch.typeText("baihe-hermes-test")
        } else {
            let phone = app.textFields["11 位手机号"]
            XCTAssertTrue(phone.waitForExistence(timeout: 4))
            phone.tap()
            phone.typeText("13800138000")
            let password = app.secureTextFields.firstMatch
            password.tap()
            password.typeText("baihe-hermes-test")
        }

        if any("phone-auth-submit").waitForExistence(timeout: 2) {
            any("phone-auth-submit").tap()
        } else {
            app.buttons["登录"].firstMatch.tap()
        }

        finishFirstUseIfNeeded()
    }

    func testPhoneLoginAndHermesTodayCourses() throws {
        app.terminate()
        app.launchArguments = ["-UIAccessibilityReduceMotionEnabled", "YES"]
        app.launch()
        dismissSystemAlertIfNeeded()

        ensureLoggedInWithPhone()
        finishFirstUseIfNeeded()

        tapTab("今天")
        XCTAssertTrue(any("screen-B1-today").waitForExistence(timeout: 10), "today screen missing")

        // Parent `today-hermes-entry` can swallow the child input identifier in the AX tree.
        // Empty ask still routes to B2 (TodayView.sendHermes).
        let askButton = app.buttons.matching(NSPredicate(format: "label == %@", "提问")).firstMatch
        if askButton.waitForExistence(timeout: 6) {
            askButton.tap()
        } else {
            let field = app.textFields["例如：按我的画像推荐公选"].firstMatch
            XCTAssertTrue(field.waitForExistence(timeout: 6), "hermes field missing on today")
            field.tap()
            field.typeText("今天有什么课\n")
        }

        XCTAssertTrue(any("screen-B2-hermes").waitForExistence(timeout: 12), "Hermes screen not open")

        let courseA = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "工业软件")).firstMatch
        let courseB = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "计算机网络")).firstMatch
        if !(courseA.waitForExistence(timeout: 8) || courseB.waitForExistence(timeout: 2)) {
            let suggestion = app.staticTexts["今天有什么课？"].firstMatch
            let suggestionButton = app.buttons["今天有什么课？"].firstMatch
            if suggestionButton.waitForExistence(timeout: 3) {
                suggestionButton.tap()
            } else if suggestion.waitForExistence(timeout: 2) {
                suggestion.tap()
            } else {
                let input = any("hermes-question-input").firstMatch
                if input.waitForExistence(timeout: 4) {
                    input.tap()
                    input.typeText("今天有什么课")
                } else {
                    let field = app.textFields.firstMatch
                    field.tap()
                    field.typeText("今天有什么课")
                }
                if app.buttons["提问"].waitForExistence(timeout: 2) {
                    app.buttons["提问"].firstMatch.tap()
                }
            }
        }

        let either = courseA.waitForExistence(timeout: 60) || courseB.waitForExistence(timeout: 5)
        XCTAssertTrue(either, "Hermes did not return real today courses from production vault")

        let shot = app.screenshot()
        let attachment = XCTAttachment(screenshot: shot)
        attachment.name = "hermes-prod-today"
        attachment.lifetime = .keepAlways
        add(attachment)
        let out = URL(fileURLWithPath: "/Users/baihe/Documents/compusone/ios/artifacts/hermes-verify/03-hermes-result.png")
        try? FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)
        try? shot.pngRepresentation.write(to: out)
    }
}
