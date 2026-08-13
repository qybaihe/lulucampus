import SwiftUI

struct CampusActionCopy: Equatable {
    struct Fact: Equatable, Identifiable {
        var id: String { label }
        let label: String
        let value: String
    }

    let title: String
    let headline: String
    let timeLine: String?
    let sticker: String
    let statusLabel: String
    let facts: [Fact]

    static func make(from result: HermesAskResult) -> CampusActionCopy? {
        guard result.kind == "action_preview"
                || result.requiresPreview
                || result.cardType == "action_preview" else {
            return nil
        }
        let root = result.data.objectValue ?? [:]
        let params = root["params"]?.objectValue ?? [:]
        return make(
            actionName: result.action,
            params: params,
            status: result.requiresPreview ? "previewed" : nil
        )
    }

    static func make(
        actionName: String?,
        params: [String: JSONValue],
        status: String? = nil
    ) -> CampusActionCopy? {
        let fields = flattenedFields(params)
        let venueType = fields["venue_type"]
        let kind = fields["kind"]
        let venue = fields["venue"]
        let room = fields["room"]
        let date = fields["date"].map(Self.formatDate)
        let start = fields["start"]
        let end = fields["end"]
        let timeRange: String?
        if let start, let end {
            timeRange = "\(start) – \(end)"
        } else {
            timeRange = start ?? end
        }
        let timeLine = [date, timeRange].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · ")

        let title = titleFor(actionName, venueType: venueType, kind: kind)
        let headlineParts: [String]
        if (actionName ?? "").hasPrefix("gym.") {
            headlineParts = [venue, venueType].compactMap { $0 }
        } else if (actionName ?? "").hasPrefix("room.") {
            headlineParts = [kind, room].compactMap { $0 }
        } else {
            headlineParts = [venue, room, kind, venueType].compactMap { $0 }
        }
        let headline = headlineParts.isEmpty ? title : headlineParts.joined(separator: " · ")

        var facts: [Fact] = []
        func add(_ label: String, _ value: String?) {
            guard let value, !value.isEmpty else { return }
            guard !facts.contains(where: { $0.label == label }) else { return }
            facts.append(Fact(label: label, value: value))
        }
        add("项目", venueType)
        add("类型", kind)
        add("地点", venue)
        add("房间", room)
        add("区域", fields["lab"])
        add("日期", date)
        add("时段", timeRange)
        add("出发", fields["from"] ?? fields["board"])
        add("到达", fields["to"] ?? fields["arrive"])
        add("用途", fields["title"])
        add("备注", fields["memo"])

        guard !facts.isEmpty || title != "校园行动" else { return nil }

        return CampusActionCopy(
            title: title,
            headline: headline,
            timeLine: timeLine.isEmpty ? nil : timeLine,
            sticker: stickerFor(actionName, venueType: venueType),
            statusLabel: statusLabel(for: status),
            facts: facts
        )
    }

    static func formatDate(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        let parts = trimmed.split(separator: "-")
        guard parts.count == 3,
              let year = Int(parts[0]),
              let month = Int(parts[1]),
              let day = Int(parts[2]) else { return trimmed }
        if trimmed == CampusDayCodec.string(from: Date()) {
            return "今晚"
        }
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = CampusDayCodec.timeZone
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = day
        components.hour = 12
        guard let date = calendar.date(from: components) else {
            return "\(month)月\(day)日"
        }
        let weekday = date.formatted(
            Date.FormatStyle().weekday(.wide).locale(Locale(identifier: "zh_CN"))
        )
        return "\(month)月\(day)日 \(weekday)"
    }
}

struct CampusActionCopyCard<Footer: View>: View {
    let copy: CampusActionCopy
    var footer: Footer

    init(copy: CampusActionCopy, @ViewBuilder footer: () -> Footer) {
        self.copy = copy
        self.footer = footer()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top, spacing: 12) {
                OMSticker(copy.sticker, size: .s56)
                VStack(alignment: .leading, spacing: 4) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(copy.title)
                            .font(OMTheme.TypeToken.title3)
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        Spacer(minLength: 8)
                        OMChip(text: copy.statusLabel, kind: .gap)
                    }
                    if copy.headline != copy.title {
                        Text(copy.headline)
                            .font(OMTheme.TypeToken.callout)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                    if let timeLine = copy.timeLine {
                        Text(timeLine)
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                    }
                }
            }

            if !copy.facts.isEmpty {
                VStack(spacing: 0) {
                    ForEach(copy.facts) { fact in
                        HStack(alignment: .firstTextBaseline, spacing: 12) {
                            Text(fact.label)
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                            Spacer(minLength: 8)
                            Text(fact.value)
                                .font(OMTheme.TypeToken.callout.weight(.semibold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                                .multilineTextAlignment(.trailing)
                        }
                        .padding(.vertical, 7)
                    }
                }
            }

            footer
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(OMTheme.ColorToken.yolk14)
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(OMTheme.ColorToken.yolkBorder, lineWidth: 1.5)
        }
        .accessibilityElement(children: .contain)
        .accessibilityIdentifier("hermes-action-copy-card")
    }
}

extension CampusActionCopyCard where Footer == EmptyView {
    init(copy: CampusActionCopy) {
        self.init(copy: copy) { EmptyView() }
    }
}

private extension CampusActionCopy {
    static let hiddenKeys: Set<String> = [
        "source", "snapshot_hash", "hash", "idempotency_key", "tool_trace",
        "action", "action_name", "commit_action_name", "params", "preview_snapshot",
        "user_id", "gathering_id", "status", "ok", "confirm_required", "seminar_id",
        "include_full", "days", "next", "message", "peers",
    ]

    static func flattenedFields(_ params: [String: JSONValue]) -> [String: String] {
        var combined = params
        if let nested = params["params"]?.objectValue {
            combined.merge(nested) { current, _ in current }
            combined.removeValue(forKey: "params")
        }
        var fields: [String: String] = [:]
        for (key, value) in combined {
            let leaf = key.split(separator: ".").last.map(String.init) ?? key
            guard !hiddenKeys.contains(leaf), !hiddenKeys.contains(key) else { continue }
            guard let text = displayText(value) else { continue }
            fields[leaf] = text
        }
        return fields
    }

    static func displayText(_ value: JSONValue) -> String? {
        switch value {
        case let .string(raw):
            let text = raw.trimmingCharacters(in: .whitespacesAndNewlines)
            if text.isEmpty { return nil }
            if text.hasPrefix("/") { return nil }
            if text.contains("_") && text.contains(".") { return nil }
            return text
        case let .number(number):
            return number.rounded() == number ? String(Int(number)) : String(number)
        case let .bool(flag):
            return flag ? "是" : "否"
        case let .array(items):
            let parts = items.compactMap(displayText)
            return parts.isEmpty ? nil : parts.joined(separator: "、")
        default:
            return nil
        }
    }

    static func titleFor(_ actionName: String?, venueType: String?, kind: String?) -> String {
        let action = actionName ?? ""
        if action.hasPrefix("gym.") { return venueType.map { "预约\($0)" } ?? "预约场馆" }
        if action.hasPrefix("room.") { return "预约研讨室" }
        if action.hasPrefix("seminar.") { return "预约讲座" }
        if action.hasPrefix("transit.qiguan") { return "岐关预约" }
        if action.hasPrefix("transit.") { return "校园班车" }
        if let kind, !kind.isEmpty { return kind }
        return "校园行动"
    }

    static func stickerFor(_ actionName: String?, venueType: String?) -> String {
        if venueType == "篮球" { return "basketball.png" }
        if venueType == "羽毛球" { return "badminton.png" }
        let action = actionName ?? ""
        if action.hasPrefix("gym.") { return "running-shoe.png" }
        if action.hasPrefix("room.") || action.hasPrefix("seminar.") { return "seminar-room-sign.png" }
        if action.hasPrefix("transit.") { return "school-bus.png" }
        return "approval-stamp.png"
    }

    static func statusLabel(for status: String?) -> String {
        switch status {
        case "succeeded": "已完成"
        case "failed": "未完成"
        case "previewed", .none: "待确认"
        default: "进行中"
        }
    }
}

extension JSONValue {
    var objectValue: [String: JSONValue]? {
        if case let .object(value) = self { return value }
        return nil
    }
}
