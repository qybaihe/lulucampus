import SwiftUI
import UIKit

/// App-facing names for the generated 2026-08-12 Lulu and sticker delivery.
/// Atlas PNGs are 2×2 sprite sheets of 627×627 cells (see lulu-motion.v1.json).
enum LuluGeneratedClip: String, CaseIterable, Sendable {
    case homeIdle = "LuluHomeIdleAtlas"
    case homeListening = "LuluHomeListeningAtlas"
    case homeThinking = "LuluHomeThinkingAtlas"
    case homeReply = "LuluHomeReplyAtlas"
    case coreStates = "LuluCoreStatesAtlas"
    case intentCard = "LuluIntentCardAtlas"
    case poolWaiting = "LuluPoolWaitingAtlas"
    case confirmGather = "LuluConfirmGatherAtlas"
    case actionPreview = "LuluActionPreviewAtlas"
    case actionExecuting = "LuluActionExecutingAtlas"
    case exitBow = "LuluExitBowAtlas"
}

enum LuluStickerBatch: String, CaseIterable, Sendable {
    case tableAndSeats = "S1"
    case sports = "S2"
    case academic = "S3"
    case campus = "S4"
    case capabilities = "S5"
    case results = "S6"
    case settings = "S7"
    case profileAndData = "S8"
    case gatheringAndRelations = "S9"
    case trustMedals = "S10"
    case scenesAndEmpty = "S11"
}

/// 65 张贴纸的 id → 批次目录（S1–S6 首批 36 张 + S7–S11 第二批 29 张）。
enum LuluStickerCatalog {
    static func batch(for id: String) -> LuluStickerBatch? {
        switch id {
        case "access-card.png", "chair-empty.png", "hourglass.png",
             "nameplate-blank.png", "qr-plaque-blank.png", "round-table.png":
            .tableAndSeats
        case "badminton.png", "basketball.png", "football.png",
             "running-shoe.png", "sports-bottle.png", "table-tennis.png":
            .sports
        case "alarm-clock.png", "books-stack.png", "desk-calendar.png",
             "laptop-closed.png", "marker.png", "notebook-open.png":
            .academic
        case "cafeteria-tray.png", "poster-blank.png", "school-bus.png",
             "seminar-room-sign.png", "study-lamp.png", "teaching-building.png":
            .campus
        case "algorithm-gear.png", "backend-server.png", "data-chart.png",
             "design-palette.png", "frontend-browser.png", "product-notes.png":
            .capabilities
        case "approval-stamp.png", "badge.png", "certificate.png",
             "chat-bubble.png", "envelope.png", "trophy.png":
            .results
        case "bell.png", "block-sign.png", "flag.png",
             "key.png", "shield-check.png", "sliders.png":
            .settings
        case "box-export.png", "clipboard-whistle.png", "id-card.png",
             "medal.png", "megaphone.png", "sparkle-wand.png":
            .profileAndData
        case "door-exit.png", "handshake.png", "party-popper.png",
             "redo-arrow.png", "table-people.png", "table-plus.png":
            .gatheringAndRelations
        case "lulu-face.png", "trust-t0.png", "trust-t1.png",
             "trust-t2.png", "trust-t3.png", "trust-t4.png":
            .trustMedals
        case "bulb.png", "cloud-off.png", "flask.png",
             "homework-pencil.png", "magnifier-empty.png":
            .scenesAndEmpty
        default:
            nil
        }
    }
}

enum LuluGeneratedAssets {
    static func atlasURL(_ clip: LuluGeneratedClip, bundle: Bundle = .main) -> URL? {
        atlasURL(named: clip.rawValue, bundle: bundle)
    }

    static func atlasURL(named assetName: String, bundle: Bundle = .main) -> URL? {
        bundle.url(forResource: assetName, withExtension: "png")
            ?? bundle.url(
                forResource: assetName,
                withExtension: "png",
                subdirectory: "LuluGenerated/Atlases"
            )
    }

    static func contractURL(bundle: Bundle = .main) -> URL? {
        bundle.url(forResource: "lulu-motion.v1", withExtension: "json")
            ?? bundle.url(
                forResource: "lulu-motion.v1",
                withExtension: "json",
                subdirectory: "LuluGenerated"
            )
    }

    static func stickerURL(
        _ id: String,
        batch: LuluStickerBatch,
        bundle: Bundle = .main
    ) -> URL? {
        let name = id.hasSuffix(".png") ? String(id.dropLast(4)) : id
        return bundle.url(forResource: name, withExtension: "png")
            ?? bundle.url(
                forResource: name,
                withExtension: "png",
                subdirectory: "LuluGenerated/Stickers/\(batch.rawValue)"
            )
    }

    static func sticker(
        _ id: String,
        batch: LuluStickerBatch,
        bundle: Bundle = .main
    ) -> UIImage? {
        stickerURL(id, batch: batch, bundle: bundle).flatMap {
            UIImage(contentsOfFile: $0.path)
        }
    }
}

struct LuluStickerImage: View {
    let id: String
    let batch: LuluStickerBatch
    var accessibilityLabel: String? = nil
    /// true = 以模板模式渲染（配合 foregroundStyle 做剪影，如已就位席位的纸色贴纸）
    var template = false

    init(id: String, batch: LuluStickerBatch, accessibilityLabel: String? = nil, template: Bool = false) {
        self.id = id
        self.batch = batch
        self.accessibilityLabel = accessibilityLabel
        self.template = template
    }

    /// 目录解析：只给贴纸 id，批次自动查表。未知 id 渲染为空。
    init(_ id: String, accessibilityLabel: String? = nil, template: Bool = false) {
        self.init(id: id, batch: LuluStickerCatalog.batch(for: id) ?? .results, accessibilityLabel: accessibilityLabel, template: template)
    }

    var body: some View {
        Group {
            if let image = LuluGeneratedAssets.sticker(id, batch: batch) {
                Image(uiImage: image)
                    .renderingMode(template ? .template : .original)
                    .resizable()
                    .interpolation(.high)
                    .scaledToFit()
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(accessibilityLabel ?? id)
    }
}
