import Foundation

/// Client-side jackpot: 很适合你 + 正好差一个角色。
/// Server scores taste_fit; the list reorder and marquee live here.
enum CompetitionSpotlight {
    private static let hotFit = 0.5

    static func gapCount(_ item: Competition) -> Int {
        if item.recruitGapCount > 0 { return item.recruitGapCount }
        for hint in item.recruitHints {
            if hint.contains("再找会"), hint.contains("的人") { return 1 }
            if let range = hint.range(of: "补上：") {
                return hint[range.upperBound...]
                    .split(separator: "、")
                    .filter { !$0.isEmpty }
                    .count
            }
        }
        return 0
    }

    static func gapLabel(_ item: Competition) -> String? {
        if gapCount(item) == 1, let label = item.recruitGapLabels.first, !label.isEmpty {
            return label
        }
        for hint in item.recruitHints {
            guard let start = hint.range(of: "再找会"), let end = hint.range(of: "的人") else { continue }
            let label = hint[start.upperBound..<end.lowerBound]
            if !label.isEmpty { return String(label) }
        }
        return nil
    }

    static func isHotSeat(_ item: Competition) -> Bool {
        guard gapCount(item) == 1 else { return false }
        if item.tasteFitLabel == "很适合你" { return true }
        return (item.tasteFit ?? 0) >= hotFit
    }

    static func fitLabel(_ item: Competition) -> String? {
        if isHotSeat(item) { return "很适合你" }
        return item.tasteFitLabel
    }

    static func chip(_ item: Competition) -> String? {
        guard isHotSeat(item) else { return nil }
        if let label = gapLabel(item) { return "正好差一个\(label)" }
        return "正好差一个"
    }

    static func isOneSeatLeft(_ team: CompetitionTeam) -> Bool {
        team.resolvedMissingCount == 1
    }

    static func isHotTeam(_ item: Competition, _ team: CompetitionTeam) -> Bool {
        isHotSeat(item) && isOneSeatLeft(team)
    }

    static func rank(_ items: [Competition]) -> [Competition] {
        items.enumerated()
            .sorted { lhs, rhs in
                let left = score(lhs.element)
                let right = score(rhs.element)
                if left != right { return left > right }
                return lhs.offset < rhs.offset
            }
            .map(\.element)
    }

    private static func score(_ item: Competition) -> Int {
        if isHotSeat(item) { return 3 }
        if item.tasteFitLabel == "很适合你" || (item.tasteFit ?? 0) >= hotFit { return 2 }
        if item.tasteFitLabel == "和你有点像" { return 1 }
        return 0
    }
}
