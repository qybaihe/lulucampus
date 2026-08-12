import CoreGraphics
import Foundation
import ImageIO
import SwiftUI
import UIKit

/// Clips used by ONE MORE screens. Raw values are clip keys in
/// `lulu-motion.v1.json`, the contract shared with the design export.
enum LuluClip: String, CaseIterable, Sendable {
    case homeIdle = "home.idle"
    case homeListening = "home.listening"
    case homeThinking = "home.thinking"
    case homeReply = "home.reply"
    case coreCare = "core.care"
    case coreCelebrate = "core.celebrate"
    case intentCard = "intent.card"
    case poolWaiting = "pool.waiting"
    case confirmGather = "confirm.gather"
    case actionPreview = "action.preview"
    case actionExecuting = "action.executing"
    case exitBow = "exit.bow"

    /// VoiceOver 用的中文状态描述
    var stateLabel: String {
        switch self {
        case .homeIdle: "待机"
        case .homeListening: "在听"
        case .homeThinking: "在想"
        case .homeReply: "回复"
        case .coreCare: "关切"
        case .coreCelebrate: "办成了"
        case .intentCard: "生成意图卡"
        case .poolWaiting: "等待凑齐"
        case .confirmGather: "等待确认"
        case .actionPreview: "行动预览"
        case .actionExecuting: "正在执行"
        case .exitBow: "鞠躬退场"
        }
    }
}

/// Decoded form of `Resources/LuluGenerated/lulu-motion.v1.json`.
struct LuluMotionContract: Decodable, Sendable {
    struct Rendering: Decodable, Sendable {
        let cellWidth: Int
        let cellHeight: Int
        let reducedMotionPolicy: String
    }
    struct Atlas: Decodable, Sendable {
        let assetName: String
        let columns: Int
        let rows: Int
    }
    struct Frame: Decodable, Sendable, Equatable {
        let cell: Int
        let durationMs: Int
    }
    struct Clip: Decodable, Sendable {
        let atlas: String
        let loopMode: String
        let posterCell: Int
        let frames: [Frame]
        var loop: Bool { loopMode == "loop" }
    }
    struct ResolvedClip: Sendable, Equatable {
        let assetName: String
        let columns: Int
        let rows: Int
        let cellWidth: Int
        let cellHeight: Int
        let loop: Bool
        let posterCell: Int
        let frames: [Frame]
    }

    let schemaVersion: Int
    let rendering: Rendering
    let atlases: [String: Atlas]
    let clips: [String: Clip]

    static func load(bundle: Bundle = .main) throws -> LuluMotionContract {
        guard let url = LuluGeneratedAssets.contractURL(bundle: bundle) else {
            throw CocoaError(.fileNoSuchFile)
        }
        return try JSONDecoder().decode(LuluMotionContract.self, from: Data(contentsOf: url))
    }

    func resolve(_ clip: LuluClip) -> ResolvedClip? {
        guard let clipValue = clips[clip.rawValue], let atlas = atlases[clipValue.atlas] else { return nil }
        return ResolvedClip(
            assetName: atlas.assetName,
            columns: atlas.columns,
            rows: atlas.rows,
            cellWidth: rendering.cellWidth,
            cellHeight: rendering.cellHeight,
            loop: clipValue.loop,
            posterCell: clipValue.posterCell,
            frames: clipValue.frames
        )
    }
}

/// Crops 2×2 atlas sheets into per-cell images, decoded off the main actor.
final class LuluAtlasCache: @unchecked Sendable {
    static let shared = LuluAtlasCache()
    private let cache = NSCache<NSString, UIImage>()
    private let bundle: Bundle

    init(bundle: Bundle = .main) {
        self.bundle = bundle
        cache.countLimit = 48
        cache.totalCostLimit = 24 * 1024 * 1024
    }

    func cellImage(assetName: String, columns: Int, rows: Int, cell: Int) async -> UIImage? {
        let key = "\(assetName)#\(cell)" as NSString
        if let cached = cache.object(forKey: key) { return cached }
        let bundle = bundle
        let scale = await MainActor.run { UIScreen.main.scale }
        let image: UIImage? = await Task.detached(priority: .utility) {
            guard let url = LuluGeneratedAssets.atlasURL(named: assetName, bundle: bundle),
                  let source = CGImageSourceCreateWithURL(url as CFURL, nil),
                  let sheet = CGImageSourceCreateImageAtIndex(source, 0, [kCGImageSourceShouldCacheImmediately: true] as CFDictionary)
            else { return nil }
            let cellW = sheet.width / columns
            let cellH = sheet.height / rows
            let col = cell % columns
            let row = cell / columns
            let rect = CGRect(x: col * cellW, y: row * cellH, width: cellW, height: cellH)
            guard let cropped = sheet.cropping(to: rect) else { return nil }
            return UIImage(cgImage: cropped, scale: scale, orientation: .up)
        }.value
        if let image {
            cache.setObject(image, forKey: key, cost: image.cgImage.map { $0.bytesPerRow * $0.height } ?? 0)
        }
        return image
    }
}

/// Plays one Lulu clip on a single visible placement. Playback pauses while
/// offscreen or backgrounded; Reduce Motion shows the contract poster frame.
@MainActor
final class LuluMotionPlayer: ObservableObject {
    @Published private(set) var image: UIImage?
    @Published private(set) var cell = 0
    @Published private(set) var isPaused = true

    private let contract: LuluMotionContract
    private let cache: LuluAtlasCache
    private var playback: Task<Void, Never>?
    private var visible = false
    private var foreground = true

    init(contract: LuluMotionContract, cache: LuluAtlasCache = .shared) {
        self.contract = contract
        self.cache = cache
    }

    convenience init(bundle: Bundle = .main) {
        self.init(contract: (try? LuluMotionContract.load(bundle: bundle)) ?? .empty)
    }

    func play(_ clip: LuluClip, reduceMotion: Bool) {
        playback?.cancel()
        guard let resolved = contract.resolve(clip) else { return }
        if reduceMotion && contract.rendering.reducedMotionPolicy == "poster-frame" {
            playback = Task { await show(resolved, cell: resolved.posterCell) }
            return
        }
        playback = Task { [weak self] in
            guard let self else { return }
            // 与 lulu.js 一致：先展示首帧，再按帧时长推进
            for frame in resolved.frames {
                if Task.isCancelled { return }
                await waitWhilePaused()
                if Task.isCancelled { return }
                await show(resolved, cell: frame.cell)
                await sleepActive(milliseconds: frame.durationMs)
            }
            if resolved.loop {
                while !Task.isCancelled {
                    for frame in resolved.frames {
                        if Task.isCancelled { return }
                        await waitWhilePaused()
                        if Task.isCancelled { return }
                        await show(resolved, cell: frame.cell)
                        await sleepActive(milliseconds: frame.durationMs)
                    }
                }
            } else {
                await show(resolved, cell: resolved.posterCell)
            }
        }
    }

    func stop() {
        playback?.cancel()
        playback = nil
    }

    func setVisible(_ value: Bool) {
        visible = value
        updatePause()
    }

    func setForeground(_ value: Bool) {
        foreground = value
        updatePause()
    }

    private func updatePause() { isPaused = !visible || !foreground }

    private func show(_ resolved: LuluMotionContract.ResolvedClip, cell: Int) async {
        guard let image = await cache.cellImage(
            assetName: resolved.assetName,
            columns: resolved.columns,
            rows: resolved.rows,
            cell: cell
        ) else { return }
        self.image = image
        self.cell = cell
    }

    private func waitWhilePaused() async {
        while isPaused && !Task.isCancelled {
            try? await Task.sleep(for: .milliseconds(20))
        }
    }

    private func sleepActive(milliseconds: Int) async {
        var remaining = milliseconds
        while remaining > 0 && !Task.isCancelled {
            if isPaused {
                try? await Task.sleep(for: .milliseconds(20))
                continue
            }
            let slice = min(remaining, 20)
            try? await Task.sleep(for: .milliseconds(slice))
            if !isPaused { remaining -= slice }
        }
    }

    deinit { playback?.cancel() }
}

extension LuluMotionContract {
    /// 契约文件缺失时的空壳，保证界面静默降级而不是崩溃。
    static let empty = LuluMotionContract(
        schemaVersion: 1,
        rendering: Rendering(cellWidth: 627, cellHeight: 627, reducedMotionPolicy: "poster-frame"),
        atlases: [:],
        clips: [:]
    )
}

enum LuluPlacement {
    case hero, header, empty, confirm, avatar

    var size: CGFloat {
        switch self {
        case .hero: OMTheme.LuluSize.hero
        case .header: OMTheme.LuluSize.header
        case .empty: OMTheme.LuluSize.empty
        case .confirm: OMTheme.LuluSize.confirm
        case .avatar: OMTheme.LuluSize.avatar
        }
    }
}

/// 与 app.css 的 `.lulu-*` 尺寸档一致；reduced-motion 落静帧。
struct LuluView: View {
    let clip: LuluClip
    var placement: LuluPlacement = .header
    var caption: String? = nil

    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var player = LuluMotionPlayer()

    var body: some View {
        VStack(spacing: 6) {
            Group {
                if let image = player.image {
                    Image(uiImage: image)
                        .resizable()
                        .interpolation(.high)
                        .scaledToFit()
                } else {
                    Color.clear
                }
            }
            .frame(width: placement.size, height: placement.size)
            .background(placement == .avatar ? OMTheme.ColorToken.card : .clear)
            .clipShape(placement == .avatar ? AnyShape(Circle()) : AnyShape(Rectangle()))
            .overlay {
                if placement == .avatar {
                    Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                }
            }
            if let caption {
                Text(caption)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .multilineTextAlignment(.center)
                    .lineSpacing(3)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(caption.map { "噜噜，\($0)" } ?? "噜噜，当前状态：\(clip.stateLabel)")
        .onAppear {
            player.setVisible(true)
            player.play(clip, reduceMotion: reduceMotion)
        }
        .onDisappear { player.setVisible(false) }
        .onChange(of: scenePhase) { _, phase in
            player.setForeground(phase == .active)
        }
        .onChange(of: reduceMotion) { _, value in
            player.play(clip, reduceMotion: value)
        }
        .onChange(of: clip) { _, newClip in
            player.play(newClip, reduceMotion: reduceMotion)
        }
    }
}

/// 生产代码的语义事件 → Lulu clip。事件名沿用旧 Azou 动效契约的调用点，
/// 只改「映射到哪只 Lulu」，不改各 Feature 的触发时机。
enum LuluMotionEvent: Sendable {
    case intentFocused
    case intentCompileStarted
    case intentPublished
    case gatheringTentative
    case poolingExpired
    case backfillStarted
    case previewReady
    case executeStarted
    case executeSucceeded
    case executeFailed
    case azouMentioned
    case azouResponseCompleted
    case humanConversationStarted

    var clip: LuluClip {
        switch self {
        case .intentFocused, .azouMentioned: .homeListening
        case .intentCompileStarted: .homeThinking
        case .azouResponseCompleted: .homeReply
        case .intentPublished: .intentCard
        case .gatheringTentative: .confirmGather
        case .poolingExpired, .executeFailed: .coreCare
        case .backfillStarted: .poolWaiting
        case .previewReady: .actionPreview
        case .executeStarted: .actionExecuting
        case .executeSucceeded: .coreCelebrate
        case .humanConversationStarted: .homeIdle
        }
    }
}

/// 全局 Lulu 状态：各 Feature 只负责 `trigger`，需要展示的地方读 `clip`。
@MainActor
final class LuluMotionEngine: ObservableObject {
    @Published private(set) var clip: LuluClip = .homeIdle

    func trigger(_ event: LuluMotionEvent, reduceMotion: Bool = UIAccessibility.isReduceMotionEnabled) {
        clip = event.clip
    }
}

#if DEBUG
/// Debug 直达证据视图：`-LuluClip home.idle` 启动参数渲染单个 clip。
struct LuluClipEvidenceView: View {
    let clip: LuluClip

    var body: some View {
        ZStack {
            OMPageBackground()
            VStack(spacing: 22) {
                Text("\(AppBrand.displayName) · 噜噜动效")
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .tracking(2)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                LuluView(clip: clip, placement: .empty)
                Text(clip.rawValue)
                    .font(OMTheme.TypeToken.mono(.title3, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
            }
            .padding(24)
        }
        .accessibilityIdentifier("lulu-evidence-\(clip.rawValue)")
    }
}
#endif
