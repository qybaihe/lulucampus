import XCTest
@testable import ONE_MORE

final class MotionEngineTests: XCTestCase {
    private func contract() throws -> LuluMotionContract {
        let url = Bundle.main.url(forResource: "lulu-motion.v1", withExtension: "json")!
        return try JSONDecoder().decode(LuluMotionContract.self, from: Data(contentsOf: url))
    }

    func testContractCoversAllTwelveClips() throws {
        let value = try contract()
        XCTAssertEqual(value.schemaVersion, 1)
        XCTAssertEqual(Set(value.clips.keys), Set(LuluClip.allCases.map(\.rawValue)))
        XCTAssertEqual(value.rendering.reducedMotionPolicy, "poster-frame")
        XCTAssertEqual(value.rendering.cellWidth, 627)
        XCTAssertEqual(value.rendering.cellHeight, 627)
    }

    func testEveryClipResolvesToARealAtlas() throws {
        let value = try contract()
        for clip in LuluClip.allCases {
            let resolved = try XCTUnwrap(value.resolve(clip), "missing clip \(clip.rawValue)")
            XCTAssertFalse(resolved.frames.isEmpty)
            XCTAssertEqual(resolved.columns, 2)
            XCTAssertEqual(resolved.rows, 2)
            XCTAssertTrue(resolved.frames.allSatisfy { $0.cell >= 0 && $0.cell < 4 && $0.durationMs > 0 })
            XCTAssertTrue((0..<4).contains(resolved.posterCell))
            XCTAssertNotNil(
                Bundle.main.url(forResource: resolved.assetName, withExtension: "png"),
                "atlas \(resolved.assetName) missing from bundle"
            )
        }
    }

    func testStickerCatalogResolvesToBundleResources() throws {
        let ids = [
            "access-card.png", "chair-empty.png", "hourglass.png", "nameplate-blank.png", "qr-plaque-blank.png", "round-table.png",
            "badminton.png", "basketball.png", "football.png", "running-shoe.png", "sports-bottle.png", "table-tennis.png",
            "alarm-clock.png", "books-stack.png", "desk-calendar.png", "laptop-closed.png", "marker.png", "notebook-open.png",
            "cafeteria-tray.png", "poster-blank.png", "school-bus.png", "seminar-room-sign.png", "study-lamp.png", "teaching-building.png",
            "algorithm-gear.png", "backend-server.png", "data-chart.png", "design-palette.png", "frontend-browser.png", "product-notes.png",
            "approval-stamp.png", "badge.png", "certificate.png", "chat-bubble.png", "envelope.png", "trophy.png",
            "bell.png", "block-sign.png", "flag.png", "key.png", "shield-check.png", "sliders.png",
            "box-export.png", "clipboard-whistle.png", "id-card.png", "medal.png", "megaphone.png", "sparkle-wand.png",
            "door-exit.png", "handshake.png", "party-popper.png", "redo-arrow.png", "table-people.png", "table-plus.png",
            "lulu-face.png", "trust-t0.png", "trust-t1.png", "trust-t2.png", "trust-t3.png", "trust-t4.png",
            "bulb.png", "cloud-off.png", "flask.png", "homework-pencil.png", "magnifier-empty.png",
        ]
        XCTAssertEqual(ids.count, 65)
        for id in ids {
            let batch = try XCTUnwrap(LuluStickerCatalog.batch(for: id), "unregistered sticker \(id)")
            XCTAssertNotNil(
                LuluGeneratedAssets.sticker(id, batch: batch),
                "sticker \(id) missing from bundle"
            )
        }
    }

    func testLoopModesMatchDesignContract() throws {
        let value = try contract()
        // once 组：intent.card / confirm.gather / action.preview / action.executing / exit.bow
        for clip in [LuluClip.intentCard, .confirmGather, .actionPreview, .actionExecuting, .exitBow] {
            XCTAssertFalse(try XCTUnwrap(value.resolve(clip)).loop, "\(clip.rawValue) must play once")
        }
        for clip in [LuluClip.homeIdle, .homeListening, .homeThinking, .homeReply, .coreCare, .coreCelebrate, .poolWaiting] {
            XCTAssertTrue(try XCTUnwrap(value.resolve(clip)).loop, "\(clip.rawValue) must loop")
        }
    }

    @MainActor
    func testPlayerPausesInBackgroundAndOffscreen() async {
        let player = LuluMotionPlayer(contract: .empty)
        player.setVisible(true)
        player.setForeground(false)
        XCTAssertTrue(player.isPaused)
        player.setForeground(true)
        XCTAssertFalse(player.isPaused)
        player.setVisible(false)
        XCTAssertTrue(player.isPaused)
    }

    @MainActor
    func testPlayerShowsPosterFrameUnderReduceMotion() async {
        let contract = try! contract()
        let player = LuluMotionPlayer(contract: contract)
        player.setVisible(true)
        player.play(.homeIdle, reduceMotion: true)
        let poster = try! XCTUnwrap(contract.resolve(.homeIdle)).posterCell
        try? await Task.sleep(for: .milliseconds(400))
        XCTAssertEqual(player.cell, poster)
        XCTAssertNotNil(player.image)
        player.stop()
    }

    @MainActor
    func testOnceClipEndsOnPosterCell() async {
        let contract = try! contract()
        let player = LuluMotionPlayer(contract: contract)
        player.setVisible(true)
        player.play(.exitBow, reduceMotion: false)
        let resolved = try! XCTUnwrap(contract.resolve(.exitBow))
        let total = resolved.frames.reduce(0) { $0 + $1.durationMs }
        try? await Task.sleep(for: .milliseconds(total + 600))
        XCTAssertEqual(player.cell, resolved.posterCell)
        player.stop()
    }
}
