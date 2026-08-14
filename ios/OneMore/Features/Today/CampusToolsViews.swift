import SwiftUI

private struct CampusPreviewRequest: Identifiable {
    let id = UUID()
    let action: String
    let params: [String: JSONValue]
}

private struct CampusCourseSelection: Identifiable {
    let id: String
}

private func jsonText(_ value: JSONValue) -> String {
    switch value {
    case let .string(value): value
    case let .number(value): value.formatted(.number.precision(.fractionLength(0...3)))
    case let .bool(value): value ? "是" : "否"
    case .null: "—"
    case let .array(value): value.isEmpty ? "[]" : "共 \(value.count) 项"
    case let .object(value): value.isEmpty ? "{}" : "共 \(value.count) 项"
    }
}

private func jsonRows(_ value: JSONValue, path: String = "结果") -> [(String, String)] {
    switch value {
    case let .object(object):
        return object.keys.sorted().flatMap { key in jsonRows(object[key] ?? .null, path: path == "结果" ? key : "\(path).\(key)") }
    case let .array(array):
        return array.enumerated().flatMap { index, item in jsonRows(item, path: "\(path)[\(index)]") }
    default:
        return [(path, jsonText(value))]
    }
}

private func actionParams(from result: HermesAskResult) -> [String: JSONValue]? {
    guard case let .object(root) = result.data,
          case let .object(params)? = root["params"] else { return nil }
    return params
}

private func hermesCardData(_ value: JSONValue) -> JSONValue {
    guard case let .object(root) = value else { return value }
    var filtered = root
    filtered.removeValue(forKey: "tool_trace")
    filtered.removeValue(forKey: "message")
    filtered.removeValue(forKey: "peers")
    return .object(filtered)
}

private func hermesPanelEyebrow(_ cardType: String) -> String {
    switch cardType {
    case "gym_slots": "场馆空档"
    case "course_list": "今日课表"
    case "assignment_list": "未交作业"
    case "room_slots": "研讨室"
    case "event_list": "校园活动"
    case "transit_list": "班车"
    case "parameter_clarification": "还差几个参数"
    case "knowledge_answer": "校园知识库"
    default: "校园查询"
    }
}

private func hermesKnowledgeHits(from data: JSONValue) -> [(title: String, snippet: String)] {
    guard case let .object(root) = data, case let .array(items) = root["hits"] else {
        return []
    }
    return items.compactMap { item in
        guard case let .object(object) = item else { return nil }
        let title: String
        if case let .string(value) = object["title"] { title = value } else { return nil }
        var snippet = ""
        if case let .string(value) = object["snippet"] { snippet = value }
        return (title, snippet)
    }
}

private func hermesPeers(from data: JSONValue) -> [HermesPeer] {
    guard case let .object(root) = data, case let .array(items) = root["peers"] else {
        return []
    }
    return items.compactMap { item in
        guard case let .object(object) = item,
              case let .string(userId) = object["user_id"],
              case let .string(displayName) = object["display_name"] else {
            return nil
        }
        let persona: String?
        if case let .string(value) = object["persona_label"] { persona = value } else { persona = nil }
        let reason: String
        if case let .string(value) = object["reason"] { reason = value } else { reason = "可能合得来" }
        let overlap: String
        if case let .string(value) = object["overlap"] { overlap = value } else { overlap = "taste" }
        return HermesPeer(
            userId: userId,
            displayName: displayName,
            personaLabel: persona,
            reason: reason,
            overlap: overlap
        )
    }
}

private struct HermesResultPanel<Content: View>: View {
    let icon: String
    let eyebrow: String
    let content: Content

    init(icon: String, eyebrow: String, @ViewBuilder content: () -> Content) {
        self.icon = icon
        self.eyebrow = eyebrow
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Text(eyebrow)
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer(minLength: 0)
            }
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(OMTheme.ColorToken.yolk)

            content
                .padding(14)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(OMTheme.ColorToken.yolk14)
        }
        .clipShape(RoundedRectangle(cornerRadius: 18, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(OMTheme.ColorToken.yolkBorder, lineWidth: 1.5)
        }
    }
}

private struct StructuredResultCard: View {
    let title: String
    let value: JSONValue
    var embedded = false

    var body: some View {
        if embedded {
            inner
        } else {
            OMCard { inner }
        }
    }

    private var inner: some View {
        VStack(alignment: .leading, spacing: 8) {
            if !title.isEmpty, !title.contains("_"), title != "action_preview" {
                Text(title)
                    .font(OMTheme.TypeToken.title3)
                    .foregroundStyle(OMTheme.ColorToken.ink)
            }
            let rows = humanRows(value)
            if rows.isEmpty {
                OMTextRole.foot("没有可展示的校园结果")
            }
            ForEach(Array(rows.prefix(12).enumerated()), id: \.offset) { _, row in
                HStack(alignment: .firstTextBaseline, spacing: 12) {
                    Text(row.0)
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                    Spacer(minLength: 8)
                    Text(row.1)
                        .font(OMTheme.TypeToken.callout.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .multilineTextAlignment(.trailing)
                        .textSelection(.enabled)
                }
                .padding(.vertical, 2)
            }
        }
    }
}

private let hermesHiddenKeys: Set<String> = [
    "next", "tool_trace", "message", "peers", "ok", "action", "params",
    "requires_preview", "preview_snapshot", "snapshot_hash", "idempotency_key",
    "user_id", "gathering_id", "commit_action_name", "action_name", "source",
    "hash", "status", "confirm_required", "include_full", "days",
]

private let hermesFieldLabels: [String: String] = [
    "date": "日期",
    "start": "开始",
    "end": "结束",
    "venue": "地点",
    "venue_type": "项目",
    "room": "房间",
    "kind": "类型",
    "lab": "区域",
    "title": "名称",
    "memo": "备注",
    "location": "地点",
    "count": "人数",
    "query": "关键词",
]

private func humanRows(_ value: JSONValue, path: String = "") -> [(String, String)] {
    switch value {
    case let .object(object):
        var combined = object
        if case let .object(nested) = object["params"] {
            combined.merge(nested) { current, _ in current }
            combined.removeValue(forKey: "params")
        }
        return combined.keys.sorted().flatMap { key -> [(String, String)] in
            let leaf = key.split(separator: ".").last.map(String.init) ?? key
            if hermesHiddenKeys.contains(leaf) || hermesHiddenKeys.contains(key) { return [] }
            if leaf.contains("id") || leaf.hasSuffix("_at") { return [] }
            return humanRows(combined[key] ?? .null, path: hermesFieldLabels[leaf] ?? (path.isEmpty ? leaf : path))
        }.filter { !$0.0.contains("_") && !$0.0.contains("/") && !$0.1.hasPrefix("/") }
    case let .array(array):
        return array.prefix(6).enumerated().flatMap { index, item in
            humanRows(item, path: path.isEmpty ? "第 \(index + 1) 项" : path)
        }
    default:
        let text = jsonText(value)
        if text == "—" || text.hasPrefix("/") || text.contains("_") && text.contains(".") { return [] }
        let label = path.isEmpty || path.contains("_") ? "内容" : path
        return [(label, text)]
    }
}

private struct ElectiveMatchCard: View {
    let data: JSONValue

    private var object: [String: JSONValue] {
        if case let .object(value) = data { return value }
        return [:]
    }

    private var items: [JSONValue] {
        if case let .array(value) = object["items"] { return value }
        return []
    }

    private func field(_ item: JSONValue, _ key: String) -> String {
        guard case let .object(obj) = item else { return "—" }
        return jsonText(obj[key] ?? .null)
    }

    private func reasons(in item: JSONValue) -> [String] {
        guard case let .object(obj) = item else { return [] }
        switch obj["match_reasons"] {
        case let .array(values):
            return values.compactMap { value in
                if case let .string(text) = value { return text }
                return nil
            }
        case let .string(text):
            return text.isEmpty ? [] : [text]
        default:
            return []
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("公选匹配")
                    .font(OMTheme.TypeToken.title3)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                Spacer(minLength: 0)
                if case let .string(label) = object["persona_label"] {
                    Text(label)
                        .font(OMTheme.TypeToken.caption.weight(.semibold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(OMTheme.ColorToken.yolk.opacity(0.55))
                        .clipShape(Capsule())
                }
            }

            if items.isEmpty, case let .string(message) = object["message"] {
                OMMarkdownText(text: message)
            }

            ForEach(Array(items.prefix(8).enumerated()), id: \.offset) { index, item in
                HStack(alignment: .top, spacing: 10) {
                    Text("\(index + 1)")
                        .font(OMTheme.TypeToken.mono(.caption, weight: .bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .frame(width: 22, height: 22)
                        .background(index == 0 ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.ink06)
                        .clipShape(Circle())

                    VStack(alignment: .leading, spacing: 4) {
                        Text(field(item, "title"))
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .fixedSize(horizontal: false, vertical: true)
                        Text(
                            [field(item, "code"), field(item, "category"), field(item, "credits") == "—" ? nil : "\(field(item, "credits")) 学分"]
                                .compactMap { $0 }
                                .filter { $0 != "—" }
                                .joined(separator: " · ")
                        )
                        .font(OMTheme.TypeToken.mono(.caption))
                        .foregroundStyle(OMTheme.ColorToken.mist)

                        HStack(spacing: 6) {
                            let competition = field(item, "competition_label")
                            if competition != "—" {
                                Text(competition)
                                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                                    .padding(.horizontal, 7)
                                    .padding(.vertical, 3)
                                    .background(OMTheme.ColorToken.card)
                                    .clipShape(Capsule())
                            }
                            let selected = field(item, "selected")
                            let capacity = field(item, "capacity")
                            if selected != "—" || capacity != "—" {
                                Text("已选 \(selected)/\(capacity)")
                                    .font(OMTheme.TypeToken.caption)
                                    .foregroundStyle(OMTheme.ColorToken.mist)
                            }
                        }

                        let reasonText = reasons(in: item).prefix(2).joined(separator: " · ")
                        if !reasonText.isEmpty {
                            Text(reasonText)
                                .font(OMTheme.TypeToken.caption)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                    }
                    Spacer(minLength: 0)
                }
                if index < min(items.count, 8) - 1 {
                    OMDivider()
                }
            }

            if let note = displayNote {
                Text(note)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .padding(.top, 2)
            }
        }
    }

    private var displayNote: String? {
        if case let .object(catalog) = object["catalog"],
           case let .string(status) = catalog["session_status"],
           status == "login_expired" {
            return "教务登录已过期，重新扫码后会更新。"
        }
        return nil
    }
}

private struct HermesPeerList: View {
    let peers: [HermesPeer]
    var startingPeerID: String?
    var error: String?
    let onStart: (HermesPeer) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("已开启社交的同学")
                .font(OMTheme.TypeToken.title3)
                .foregroundStyle(OMTheme.ColorToken.ink)
            ForEach(Array(peers.enumerated()), id: \.element.id) { index, peer in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(alignment: .firstTextBaseline, spacing: 8) {
                        Text(peer.displayName)
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                        if let label = peer.personaLabel, !label.isEmpty {
                            Text(label)
                                .font(OMTheme.TypeToken.caption.weight(.semibold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 3)
                                .background(OMTheme.ColorToken.yolk.opacity(0.55))
                                .clipShape(Capsule())
                        }
                        Spacer(minLength: 0)
                    }
                    Text(peer.reason)
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                    OMButton(
                        "一键发起聊天",
                        systemIcon: "bubble.left.and.bubble.right",
                        kind: .ghost,
                        small: true,
                        loading: startingPeerID == peer.userId
                    ) {
                        onStart(peer)
                    }
                    .accessibilityIdentifier("hermes-start-peer-chat-\(peer.userId)")
                }
                if index < peers.count - 1 {
                    OMDivider()
                }
            }
            if let error, !error.isEmpty {
                Text(error)
                    .font(OMTheme.TypeToken.footnote)
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
        }
    }
}

private enum HermesMessageKind {
    case user
    case thinking
    case tool
    case answer
    case result
    case error
}

private struct HermesChatMessage: Identifiable, Equatable {
    let id: UUID
    var kind: HermesMessageKind
    var text: String
    var toolName: String? = nil
    var result: HermesAskResult? = nil
    var isActive: Bool = false

    static func == (lhs: HermesChatMessage, rhs: HermesChatMessage) -> Bool {
        lhs.id == rhs.id
            && lhs.kind == rhs.kind
            && lhs.text == rhs.text
            && lhs.toolName == rhs.toolName
            && lhs.isActive == rhs.isActive
            && lhs.result?.cardType == rhs.result?.cardType
            && lhs.result?.kind == rhs.result?.kind
    }
}

@MainActor private final class HermesAskViewModel: ObservableObject {
    @Published var text = ""
    @Published var messages: [HermesChatMessage] = []
    @Published var result: HermesAskResult?
    @Published var working = false
    @Published var error: String?
    @Published var scrollToken = UUID()
    @Published var startingPeerID: String?
    @Published var peerError: String?

    static let suggestions = [
        "按我的画像推荐公选",
        "今天有什么课？",
        "宿舍晚上会断电吗？",
        "还有谁也选了机器学习？",
        "还有谁也约了羽毛球？",
    ]

    private let repository: TodayRepository
    init(repository: TodayRepository) { self.repository = repository }

    var canSend: Bool {
        !working && !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    func ask(_ preset: String? = nil) async {
        let query = (preset ?? text).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !working, !query.isEmpty else { return }
        working = true
        error = nil
        result = nil
        if preset == nil { text = "" }

        messages.append(HermesChatMessage(id: UUID(), kind: .user, text: query))
        let thinkingID = UUID()
        messages.append(
            HermesChatMessage(
                id: thinkingID,
                kind: .thinking,
                text: "正在询问校园 Agent…",
                isActive: true
            )
        )
        bumpScroll()

        do {
            let asked = try await repository.askHermes(query)
            result = asked
            if let index = messages.firstIndex(where: { $0.id == thinkingID }) {
                messages[index].text = asked.toolTrace?.isEmpty == false ? "已理解意图，正在调用校园工具" : "已完成回复"
                messages[index].isActive = false
            }
            let traces = asked.toolTrace ?? Self.toolTrace(from: asked.data)
            for trace in traces {
                messages.append(
                    HermesChatMessage(
                        id: UUID(),
                        kind: .tool,
                        text: trace.summary?.isEmpty == false ? (trace.summary ?? "已完成") : (trace.ok == false ? "调用失败" : "已完成"),
                        toolName: trace.name,
                        isActive: false
                    )
                )
            }
            let answer = Self.answerText(for: asked)
            messages.append(
                HermesChatMessage(id: UUID(), kind: .answer, text: answer)
            )
            messages.append(
                HermesChatMessage(id: UUID(), kind: .result, text: asked.cardType, result: asked)
            )
        } catch {
            if let index = messages.firstIndex(where: { $0.id == thinkingID }) {
                messages[index].text = "询问失败"
                messages[index].isActive = false
            }
            let message = error.localizedDescription
            self.error = message
            messages.append(
                HermesChatMessage(id: UUID(), kind: .error, text: message)
            )
        }
        working = false
        bumpScroll()
    }

    func startChat(with peer: HermesPeer, router: AppRouter) async {
        guard startingPeerID == nil else { return }
        startingPeerID = peer.userId
        peerError = nil
        defer { startingPeerID = nil }
        do {
            let opened = try await repository.startHermesPeerChat(
                peerUserID: peer.userId,
                reason: peer.reason,
                overlap: peer.overlap
            )
            router.push(.channel(opened.channelId))
        } catch {
            peerError = error.localizedDescription
        }
        bumpScroll()
    }

    private func bumpScroll() { scrollToken = UUID() }

    private static func toolTrace(from data: JSONValue) -> [HermesToolTrace] {
        guard case let .object(root) = data, case let .array(items) = root["tool_trace"] else {
            return []
        }
        return items.compactMap { item in
            guard case let .object(object) = item, case let .string(name) = object["name"] else {
                return nil
            }
            let ok: Bool?
            if case let .bool(value) = object["ok"] { ok = value } else { ok = nil }
            let summary: String?
            if case let .string(value) = object["summary"] { summary = value } else { summary = nil }
            let cardType: String?
            if case let .string(value) = object["card_type"] { cardType = value } else { cardType = nil }
            return HermesToolTrace(name: name, ok: ok, summary: summary, cardType: cardType)
        }
    }

    private static func answerText(for result: HermesAskResult) -> String {
        let hasItems: Bool = {
            guard case let .object(root) = result.data, case let .array(items) = root["items"] else {
                return false
            }
            return !items.isEmpty
        }()
        if case let .object(root) = result.data, case let .string(message) = root["message"] {
            return compactHermesMessage(message, cardType: result.cardType, hasStructuredItems: hasItems)
        }
        switch result.kind {
        case "help":
            return "我主要处理课表、DDL、场地、活动、班车、校园日常知识，以及按画像推荐公选。"
        case "clarification":
            return "还差几个参数，补齐后我就能继续查。"
        case "action_preview":
            return "已生成预览，确认后再执行。"
        default:
            if result.cardType == "elective_match" {
                return "按你的画像挑了这几门。"
            }
            return "查到了，结果在下面。"
        }
    }

    private static func compactHermesMessage(
        _ raw: String,
        cardType: String,
        hasStructuredItems: Bool
    ) -> String {
        var text = stripBoilerplate(raw)
        if hasStructuredItems {
            if let range = text.range(of: #"\n?\s*1[\.、]"#, options: .regularExpression) {
                text = String(text[..<range.lowerBound])
            }
            for marker in ["几点提醒", "提醒一句", "想再按", "需要我帮你", "要不要我"] {
                if let range = text.range(of: marker) {
                    text = String(text[..<range.lowerBound])
                }
            }
        }
        text = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty {
            return cardType == "elective_match" ? "按你的画像挑了这几门。" : "查到了。"
        }
        return text
    }

    private static func stripBoilerplate(_ raw: String) -> String {
        var text = raw
        let patterns = [
            #"提醒一句[：:].*?(不会自动帮你选课|不会自动选课)[。.]?"#,
            #"这只是只读推荐[^。\n]*[。.]?"#,
            #"只读推荐[，,]不会自动选课[。.]?"#,
            #"正式选课请在教务确认[。.]?"#,
            #"不会自动帮你选课[。.]?"#,
            #"不会自动选课[。.]?"#,
            #"不会代选课[。.]?"#,
        ]
        for pattern in patterns {
            text = text.replacingOccurrences(of: pattern, with: "", options: .regularExpression)
        }
        return text.replacingOccurrences(of: #"\n{3,}"#, with: "\n\n", options: .regularExpression)
    }
}

/// B2 · 问问 Hermes（对话式）
struct HermesAskView: View {
    @StateObject private var model: HermesAskViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var preview: CampusPreviewRequest?
    @FocusState private var inputFocused: Bool

    init(repository: TodayRepository) {
        _model = StateObject(wrappedValue: HermesAskViewModel(repository: repository))
    }

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        hermesIntro
                        if model.messages.isEmpty {
                            suggestionChips
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        ForEach(model.messages) { message in
                            hermesRow(message)
                                .id(message.id)
                        }
                        Color.clear.frame(height: 8).id("hermes-bottom")
                    }
                    .padding(.horizontal, OMTheme.Spacing.pageX)
                    .padding(.top, OMTheme.Spacing.s2)
                    .padding(.bottom, OMTheme.Spacing.s4)
                }
                .onChange(of: model.scrollToken) { _, _ in
                    withAnimation(OMTheme.Motion.medium) {
                        proxy.scrollTo("hermes-bottom", anchor: .bottom)
                    }
                }
            }

            composer
        }
        .background(OMPageBackground())
        .onAppear {
            if let draft = router.hermesDraft {
                router.hermesDraft = nil
                Task { await model.ask(draft) }
            }
        }
        .sheet(item: $preview) { request in
            PersonalActionPreviewView(
                action: request.action, params: request.params,
                repository: environment.actions
            )
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B2-hermes")
    }

    private var hermesIntro: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 10) {
                LuluView(clip: .homeListening, placement: .avatar)
                VStack(alignment: .leading, spacing: 2) {
                    Text(AppBrand.agentName)
                        .font(OMTheme.TypeToken.title3)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    Text("校园事务助手 · 会先想清楚再查工具")
                        .font(OMTheme.TypeToken.caption)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
                Spacer(minLength: 0)
            }
            OMSysBubble(text: "课表 · DDL · 场地 · 公选 · 同课/同时段的人")
        }
    }

    private var suggestionChips: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("试试这样问")
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
            FlowSuggestionWrap(items: HermesAskViewModel.suggestions) { item in
                Task { await model.ask(item) }
            }
        }
    }

    @ViewBuilder
    private func hermesRow(_ message: HermesChatMessage) -> some View {
        switch message.kind {
        case .user:
            OMChatBubble(message.text, mine: true)
        case .thinking, .tool:
            HermesAgentStepRow(
                kind: message.kind,
                text: message.text,
                toolName: message.toolName,
                isActive: message.isActive
            )
        case .answer:
            HStack(alignment: .top, spacing: 8) {
                LuluView(clip: .homeReply, placement: .avatar)
                OMChatBubble(message.text, mine: false, markdown: true)
            }
        case .result:
            if let result = message.result {
                VStack(alignment: .leading, spacing: 10) {
                    if result.cardType == "elective_match" {
                        HermesResultPanel(icon: "sparkles", eyebrow: "匹配结果") {
                            ElectiveMatchCard(data: result.data)
                        }
                    } else if let copy = CampusActionCopy.make(from: result) {
                        CampusActionCopyCard(copy: copy) {
                            if result.requiresPreview,
                               let action = result.action,
                               let params = actionParams(from: result) {
                                OMButton("去核对预约", systemIcon: "checkmark.seal", kind: .ghost, small: true) {
                                    preview = CampusPreviewRequest(action: action, params: params)
                                }
                                .accessibilityIdentifier("hermes-open-action-preview")
                            }
                        }
                    } else if result.cardType != "peer_list"
                                && result.kind != "help"
                                && result.cardType != "agent_reply"
                                && result.cardType != "knowledge_answer"
                                && result.kind != "clarification" {
                        HermesResultPanel(icon: "doc.text", eyebrow: hermesPanelEyebrow(result.cardType)) {
                            StructuredResultCard(title: "", value: hermesCardData(result.data), embedded: true)
                        }
                    }
                    let knowledgeHits = hermesKnowledgeHits(from: result.data)
                    if !knowledgeHits.isEmpty {
                        HermesResultPanel(icon: "books.vertical.fill", eyebrow: "依据校园知识库") {
                            VStack(alignment: .leading, spacing: 8) {
                                ForEach(Array(knowledgeHits.enumerated()), id: \.offset) { _, hit in
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text(hit.title)
                                            .font(OMTheme.TypeToken.callout)
                                        if !hit.snippet.isEmpty {
                                            Text(hit.snippet)
                                                .font(OMTheme.TypeToken.caption)
                                                .foregroundStyle(OMTheme.ColorToken.mist)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    let peers = hermesPeers(from: result.data)
                    if !peers.isEmpty {
                        HermesResultPanel(icon: "person.2.fill", eyebrow: "可能合得来的人") {
                            HermesPeerList(
                                peers: peers,
                                startingPeerID: model.startingPeerID,
                                error: model.peerError
                            ) { peer in
                                Task { await model.startChat(with: peer, router: router) }
                            }
                        }
                    }
                    if result.kind == "clarification", let action = result.action {
                        OMButton("补齐参数后继续", systemIcon: "slider.horizontal.3", kind: .ghost, small: true) {
                            router.push(.formalOrScreen(
                                CampusActionExecutionDisposition.recoveryScreen(actionName: action)
                            ))
                        }
                    }
                    if result.requiresPreview,
                       CampusActionCopy.make(from: result) == nil,
                       let action = result.action,
                       let params = actionParams(from: result) {
                        OMButton("去核对预约", systemIcon: "checkmark.seal", kind: .ghost, small: true) {
                            preview = CampusPreviewRequest(action: action, params: params)
                        }
                        .accessibilityIdentifier("hermes-open-action-preview")
                    }
                }
            }
        case .error:
            OMCard {
                OMG5StateView(state: .networkError, message: message.text)
            }
        }
    }

    private var composer: some View {
        VStack(spacing: 0) {
            Rectangle()
                .fill(OMTheme.ColorToken.line)
                .frame(height: OMTheme.Radius.borderWidth)
            HStack(alignment: .bottom, spacing: 8) {
                TextField("问校园相关的事…", text: $model.text, axis: .vertical)
                    .font(OMTheme.TypeToken.callout)
                    .lineLimit(1...5)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .focused($inputFocused)
                    .accessibilityIdentifier("hermes-question-input")
                    .background(OMTheme.ColorToken.card)
                    .clipShape(RoundedRectangle(cornerRadius: 22, style: .continuous))
                    .overlay {
                        RoundedRectangle(cornerRadius: 22, style: .continuous)
                            .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                    }
                    .onSubmit { Task { await model.ask() } }

                Button {
                    Task { await model.ask() }
                } label: {
                    Group {
                        if model.working {
                            ProgressView()
                                .tint(OMTheme.ColorToken.paper)
                        } else {
                            Image(systemName: "arrow.up")
                                .font(.system(size: 16, weight: .semibold))
                                .foregroundStyle(OMTheme.ColorToken.paper)
                        }
                    }
                    .frame(width: 42, height: 42)
                    .background(model.canSend || model.working ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist40)
                    .clipShape(Circle())
                }
                .buttonStyle(OMButtonPressStyle())
                .disabled(!model.canSend && !model.working)
                .accessibilityLabel("发送")
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.top, 10)
            .padding(.bottom, 12)
            .background(OMTheme.ColorToken.paper.opacity(0.96))
        }
    }
}

private struct HermesAgentStepRow: View {
    let kind: HermesMessageKind
    let text: String
    var toolName: String? = nil
    var isActive = false

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            Group {
                if isActive {
                    ProgressView()
                        .controlSize(.small)
                } else {
                    Image(systemName: kind == .tool ? "wrench.and.screwdriver" : "sparkles")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
            }
            .frame(width: 18, height: 18)

            VStack(alignment: .leading, spacing: 2) {
                Text(kind == .tool ? "调用工具" : "思考")
                    .font(OMTheme.TypeToken.caption.weight(.semibold))
                    .foregroundStyle(OMTheme.ColorToken.mist)
                HStack(spacing: 6) {
                    if let toolName {
                        Text(toolName)
                            .font(OMTheme.TypeToken.mono(.caption2))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(OMTheme.ColorToken.ink06)
                            .clipShape(Capsule())
                    }
                    Text(text)
                        .font(OMTheme.TypeToken.footnote)
                        .foregroundStyle(OMTheme.ColorToken.mist)
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(OMTheme.ColorToken.card.opacity(0.7))
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay {
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
        }
    }
}

private struct FlowSuggestionWrap: View {
    let items: [String]
    let onTap: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(items, id: \.self) { item in
                Button {
                    onTap(item)
                } label: {
                    Text(item)
                        .font(OMTheme.TypeToken.callout)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 9)
                        .background(OMTheme.ColorToken.card)
                        .clipShape(Capsule())
                        .overlay {
                            Capsule().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                        }
                }
                .buttonStyle(OMButtonPressStyle())
            }
        }
    }
}

@MainActor private final class PersonalActionPreviewModel: ObservableObject {
    enum Phase { case loading, loaded(CampusAction), failed(String) }
    @Published var phase: Phase = .loading
    @Published var working = false
    private let action: String
    private let params: [String: JSONValue]
    private let repository: ActionRepository
    init(action: String, params: [String: JSONValue], repository: ActionRepository) {
        self.action = action; self.params = params; self.repository = repository
    }
    func load() async {
        phase = .loading
        do { phase = .loaded(try await repository.preview(action: action, params: params, gatheringID: nil)) }
        catch { phase = .failed(error.localizedDescription) }
    }
    /// Returns true only for a session-expiry failure so the caller can keep
    /// the exact action route journaled for post-authentication recovery.
    func authorize(_ item: CampusAction) async -> Bool {
        guard !working else { return false }; working = true; defer { working = false }
        do { phase = .loaded(try await repository.authorize(item, authorized: true)); return false }
        catch {
            phase = .failed(error.localizedDescription)
            if case APIClientError.sessionExpired = error { return true }
            return false
        }
    }
    func execute(_ item: CampusAction) async -> Bool {
        guard !working else { return false }; working = true; defer { working = false }
        do { phase = .loaded(try await repository.execute(item)); return false }
        catch {
            phase = .failed(error.localizedDescription)
            if case APIClientError.sessionExpired = error { return true }
            return false
        }
    }
    func reload(_ id: String) async {
        phase = .loading
        do { phase = .loaded(try await repository.detail(id)) }
        catch { phase = .failed(error.localizedDescription) }
    }
}

/// B11 · 个人行动预览
struct PersonalActionPreviewView: View {
    @StateObject private var model: PersonalActionPreviewModel
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    init(action: String, params: [String: JSONValue], repository: ActionRepository) {
        _model = StateObject(wrappedValue: PersonalActionPreviewModel(action: action, params: params, repository: repository))
    }
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "行动预览", title: "个人行动预览", lulu: .actionPreview)
                    switch model.phase {
                    case .loading:
                        OMCard { OMG5StateView(state: .loading, message: "正在生成预览…") }
                    case let .failed(message):
                        OMCard {
                            OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                                Task { await model.load() }
                            }
                        }
                    case let .loaded(item): actionView(item)
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } } }
            .task { await model.load() }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B11-personal-action-preview")
        }
    }
    @ViewBuilder private func actionView(_ item: CampusAction) -> some View {
        if let copy = CampusActionCopy.make(
            actionName: item.actionName,
            params: item.params,
            status: item.status == "previewed" ? "previewed" : item.status,
            previewSnapshot: item.previewSnapshot
        ) {
            CampusActionCopyCard(copy: copy)
        } else {
            OMCard {
                OMTextRole.t3("预约预览")
                ForEach(Array(humanRows(.object(item.params)).enumerated()), id: \.offset) { _, row in
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(row.0)
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                        Spacer()
                        Text(row.1)
                            .font(OMTheme.TypeToken.callout.weight(.semibold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .multilineTextAlignment(.trailing)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
            }
        }
        OMCard {
            HStack(spacing: 10) {
                OMSticker("shield-check.png", size: .s44)
                OMTextRole.t3("只影响你自己的校园账户")
                Spacer()
            }
        }
        if item.status == "succeeded" {
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("approval-stamp.png", size: .s44)
                    OMTextRole.t3("行动已执行")
                    Spacer()
                }
                if let result = item.executionResult {
                    ForEach(Array(jsonRows(.object(result)).enumerated()), id: \.offset) { _, row in
                        Text("\(row.0) · \(row.1)")
                            .font(OMTheme.TypeToken.footnote)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .padding(.top, 4)
                    }
                }
            }
            if item.gatheringId == nil {
                PersonalActionCalendarControls(item: item)
            }
        } else if item.status == "failed" {
            actionFailureView(item)
        } else if item.isReferencePreview {
            OMCard {
                OMTextRole.t3("这是找球友的时段参考")
                OMTextRole.foot("不是要提交的预约，不用核对。")
                    .padding(.top, 4)
            }
            OMButton("知道了") { dismiss() }
        } else if item.authorization.actorDecision != "authorized" {
            OMButton("我已核对，授权此预览", systemIcon: "checkmark.shield", loading: model.working) {
                preserveRecovery(for: item.id)
                Task { clearRecovery(unlessSessionExpired: await model.authorize(item)) }
            }
        } else {
            OMButton("执行校园行动", systemIcon: "bolt.fill", loading: model.working, disabledReason: item.authorization.allAuthorized ? nil : "授权状态尚未同步") {
                preserveRecovery(for: item.id)
                Task { clearRecovery(unlessSessionExpired: await model.execute(item)) }
            }
        }
    }

    @ViewBuilder private func actionFailureView(_ item: CampusAction) -> some View {
        let disposition = CampusActionExecutionDisposition.resolve(
            status: item.status, errorCategory: item.errorCategory
        )
        OMCard {
            HStack(spacing: 10) {
                Image(om: .warn)
                    .font(.system(size: 17))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .frame(width: 38, height: 38)
                    .background(OMTheme.ColorToken.gapSoft)
                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("校园操作未执行")
                    OMTextRole.foot(actionFailureMessage(disposition))
                }
                Spacer()
            }
            if let category = item.errorCategory {
                Text("错误分类 · \(category)")
                    .font(OMTheme.TypeToken.mono(.caption))
                    .foregroundStyle(OMTheme.ColorToken.mist)
                    .textSelection(.enabled)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
        switch disposition {
        case .reauthenticate:
            OMButton("重新认证并返回此操作", icon: .scan) {
                preserveRecovery(for: item.id)
                dismiss()
                router.recoverAfterSessionExpired(.action(item.id))
            }
        case .chooseAnotherResource, .invalidParameters:
            OMButton("返回参数页重新选择", systemIcon: "slider.horizontal.3") {
                dismiss()
                router.push(.formalOrScreen(CampusActionExecutionDisposition.recoveryScreen(actionName: item.actionName)))
            }
        case .retryLater, .unknownFailure:
            OMButton("刷新服务端状态", systemIcon: "arrow.clockwise", loading: model.working) {
                Task { await model.reload(item.id) }
            }
            OMButton("返回校园工具，稍后重新生成", kind: .ghost) {
                dismiss()
                router.push(.formal(.b2))
            }
            .padding(.top, OMTheme.Spacing.s2)
        case .succeeded:
            EmptyView()
        }
    }

    private func preserveRecovery(for actionID: String) {
        let route = AppRoute.action(actionID)
        router.pendingAfterAuthentication = route
        environment.recovery.saveExternalRoute(route)
    }

    private func clearRecovery(unlessSessionExpired sessionExpired: Bool) {
        guard !sessionExpired else { return }
        if case .action = router.pendingAfterAuthentication { router.pendingAfterAuthentication = nil }
        environment.recovery.clearExternalRoute()
    }
}

private struct PersonalActionCalendarControls: View {
    let item: CampusAction
    @EnvironmentObject private var environment: AppEnvironment
    @State private var scope = "anonymous"
    @State private var eventExists = false
    @State private var working = false
    @State private var permissionDenied = false
    @State private var message: String?

    private var actionKey: String { "action:\(item.id)" }
    private var descriptor: CalendarEventDescriptor? {
        PersonalActionCalendarDescriptorFactory.make(
            actionID: item.id,
            actionName: item.actionName,
            params: item.params
        )
    }

    var body: some View {
        if let descriptor {
            OMCard {
                HStack(spacing: 10) {
                    OMSticker("desk-calendar.png", size: .s44)
                    OMTextRole.t3("同步到系统日历")
                    Spacer()
                }
                OMButton(
                    eventExists ? "更新系统日历" : "添加到系统日历",
                    systemIcon: eventExists ? "calendar.badge.clock" : "calendar.badge.plus",
                    loading: working
                ) { Task { await addOrUpdate(descriptor) } }
                .padding(.top, OMTheme.Spacing.s3)
                .accessibilityIdentifier("personal-action-calendar-sync")
                if eventExists {
                    OMButton("从系统日历删除", kind: .ghost) { Task { await remove() } }
                        .padding(.top, OMTheme.Spacing.s2)
                        .accessibilityIdentifier("personal-action-calendar-delete")
                }
                if permissionDenied {
                    OMTextRole.foot("日历权限未开启；系统没有写入任何事件。")
                        .padding(.top, OMTheme.Spacing.s2)
                    OMButton("打开系统设置", kind: .text, small: true, fillsWidth: false) {
                        environment.permissions.openSystemSettings()
                    }
                }
                if let message {
                    OMTextRole.cap(message).padding(.top, OMTheme.Spacing.s2)
                }
            }
            .task(id: item.id) {
                scope = await environment.auth.cacheScope()
                eventExists = await environment.calendarReconciler.hasEvent(
                    gatheringID: actionKey,
                    scope: scope
                )
            }
        }
    }

    @MainActor private func addOrUpdate(_ descriptor: CalendarEventDescriptor) async {
        guard !working else { return }
        working = true; message = nil
        defer { working = false }
        do {
            _ = try await environment.calendarReconciler.addOrUpdate(
                gatheringID: actionKey,
                scope: scope,
                descriptor: descriptor,
                requestAccess: true
            )
            eventExists = true
            permissionDenied = false
            environment.permissions.recordAuthorization(.calendar, granted: true)
            message = "已同步；再次执行会更新同一事件。"
        } catch {
            if case CalendarReconciliationError.accessDenied = error {
                permissionDenied = true
                environment.permissions.recordAuthorization(.calendar, granted: false)
            }
            message = error.localizedDescription
        }
    }

    @MainActor private func remove() async {
        guard !working else { return }
        working = true; message = nil
        defer { working = false }
        do {
            _ = try await environment.calendarReconciler.removeIfPresent(
                gatheringID: actionKey,
                scope: scope
            )
            eventExists = false
            message = "已从系统日历删除。"
        } catch {
            message = error.localizedDescription
        }
    }
}

private func actionFailureMessage(_ disposition: CampusActionExecutionDisposition) -> String {
    switch disposition {
    case .reauthenticate: "校园登录已失效；完成重新认证后会回到同一行动，不会伪装执行成功。"
    case .chooseAnotherResource: "原资源已冲突；旧预览已经失效，请重新选择资源并生成新预览。"
    case .retryLater: "校园系统正在限流或维护；请稍后重新生成预览。"
    case .invalidParameters: "参数或响应已失效；请回到参数页修正后生成新预览。"
    case .unknownFailure: "校园操作未完成；可刷新服务端状态，或回到校园工具重新生成。"
    case .succeeded: "行动已完成。"
    }
}

/// 周历上的一个日程块：课程或约局，统一画进网格。
private struct ScheduleBlock: Identifiable {
    enum Kind { case course(Timetable.Entry), gathering(GatheringSummary) }
    let id: String
    let title: String
    let start: Date
    let end: Date
    let detail: String?
    let kind: Kind

    var isGathering: Bool { if case .gathering = kind { true } else { false } }
    var isChangedCourse: Bool { if case let .course(entry) = kind { entry.changed } else { false } }
}

@MainActor private final class ScheduleViewModel: ObservableObject {
    struct WeekData {
        let timetable: Timetable
        /// 该周周一 0 点；空课周由已知周基准推算，推不出为 nil。
        let weekStart: Date?
        let blocks: [ScheduleBlock]
    }
    enum Phase { case loading, loaded(WeekData), failed(String) }
    @Published var week = 1
    @Published var phase: Phase = .loading
    private let repository: TodayRepository
    private let gatherings: GatheringRepository
    /// (周号, 周一) 基准：有课的周建立，空课周据此推日期。
    private var anchor: (week: Int, monday: Date)?
    private var cachedGatherings: [GatheringSummary]?
    private var didAutoLocateToday = false

    init(repository: TodayRepository, gatherings: GatheringRepository) {
        self.repository = repository
        self.gatherings = gatherings
    }

    private static var calendar: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.firstWeekday = 2
        return calendar
    }()

    func load() async {
        phase = .loading
        do {
            async let timetableTask = repository.timetable(week: week)
            if cachedGatherings == nil {
                cachedGatherings = (try? await gatherings.mine()) ?? []
            }
            let timetable = try await timetableTask
            let data = build(timetable: timetable, gatherings: cachedGatherings ?? [])
            phase = .loaded(data)
            autoLocateTodayIfNeeded(from: data)
        } catch { phase = .failed(error.localizedDescription) }
    }

    /// 今天所在周的周号；没有基准时未知。
    var currentWeek: Int? {
        guard let anchor else { return nil }
        let monday = Self.startOfWeek(Date())
        let days = Self.calendar.dateComponents([.day], from: anchor.monday, to: monday).day ?? 0
        let target = anchor.week + Int((Double(days) / 7).rounded())
        return (1...30).contains(target) ? target : nil
    }

    private func autoLocateTodayIfNeeded(from data: WeekData) {
        guard !didAutoLocateToday else { return }
        didAutoLocateToday = true
        guard let weekStart = data.weekStart else { return }
        let today = Date()
        let weekEnd = Self.calendar.date(byAdding: .day, value: 7, to: weekStart)!
        if !(weekStart...weekEnd).contains(today), let target = currentWeek, target != week {
            week = target
        }
    }

    private func build(timetable: Timetable, gatherings: [GatheringSummary]) -> WeekData {
        var monday: Date?
        if let earliest = timetable.entries.map(\.startAt).min() {
            monday = Self.startOfWeek(earliest)
            anchor = (week, monday!)
        } else if let anchor {
            monday = Self.calendar.date(byAdding: .day, value: 7 * (week - anchor.week), to: anchor.monday)
        }
        var blocks: [ScheduleBlock] = timetable.entries.map { entry in
            ScheduleBlock(
                id: "c-\(entry.id)",
                title: entry.displayTitle,
                start: entry.startAt,
                end: entry.endAt,
                detail: entry.location,
                kind: .course(entry)
            )
        }
        if let monday, let weekEnd = Self.calendar.date(byAdding: .day, value: 7, to: monday) {
            let hidden: Set<GatheringStatus> = [.draft, .dissolved, .archived, .unknown]
            for gathering in gatherings where !hidden.contains(gathering.status) {
                guard let start = gathering.startAt, start >= monday, start < weekEnd else { continue }
                blocks.append(ScheduleBlock(
                    id: "g-\(gathering.id)",
                    title: gathering.title,
                    start: start,
                    end: gathering.endAt ?? start.addingTimeInterval(3600),
                    detail: gathering.location ?? gathering.campus,
                    kind: .gathering(gathering)
                ))
            }
        }
        return WeekData(timetable: timetable, weekStart: monday, blocks: blocks)
    }

    private static func startOfWeek(_ date: Date) -> Date {
        let components = calendar.dateComponents([.yearForWeekOfYear, .weekOfYear], from: date)
        return calendar.date(from: components) ?? calendar.startOfDay(for: date)
    }
}

/// B3 · 我的日程：课程 + 约局融合的周历。
struct TimetableView: View {
    @StateObject private var model: ScheduleViewModel
    @EnvironmentObject private var router: AppRouter
    @State private var courseSelection: CampusCourseSelection?
    /// 3 天窗口的起始列（0=周一 … 4=周五起）。
    @State private var windowStart = 0
    /// 横滑切周后希望停靠的窗口位置（向前翻停周一，向后翻停周末）。
    @State private var pendingWindow: Int?
    private let repository: TodayRepository

    init(repository: TodayRepository, gatherings: GatheringRepository) {
        self.repository = repository
        _model = StateObject(wrappedValue: ScheduleViewModel(repository: repository, gatherings: gatherings))
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(title: "我的日程", lulu: .homeIdle)
                weekSwitcher
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(data):
                    loaded(data)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task(id: model.week) {
            await model.load()
            locateWindow()
        }
        .sheet(item: $courseSelection) { selection in
            CourseDetailView(id: selection.id, repository: repository)
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B3-timetable")
    }

    /// 横滑切周时优先停到指定位置；否则本周含今天对准今天，不含则回到周一。
    private func locateWindow() {
        if let pending = pendingWindow {
            pendingWindow = nil
            windowStart = pending
            return
        }
        guard case let .loaded(data) = model.phase, let weekStart = data.weekStart else { return }
        let calendar = Calendar.current
        let index = calendar.dateComponents([.day], from: weekStart, to: calendar.startOfDay(for: Date())).day ?? -1
        windowStart = (0..<7).contains(index) ? min(index, 4) : 0
    }

    @ViewBuilder private func loaded(_ data: ScheduleViewModel.WeekData) -> some View {
        legend
        if let weekStart = data.weekStart {
            OMCard(tight: true) {
                WeekScheduleGrid(
                    weekStart: weekStart,
                    blocks: data.blocks,
                    windowStart: $windowStart,
                    onOverflow: { direction in
                        let target = model.week + direction
                        guard (1...30).contains(target) else { return }
                        pendingWindow = direction > 0 ? 0 : 4
                        model.week = target
                    }
                ) { block in
                    switch block.kind {
                    case let .course(entry): courseSelection = .init(id: entry.courseId)
                    case let .gathering(gathering): router.push(.gathering(gathering.id))
                    }
                }
            }
            if data.blocks.isEmpty {
                OMTextRole.cap("这周暂时空着；发起一局，让它热闹起来。")
                    .frame(maxWidth: .infinity)
                    .multilineTextAlignment(.center)
                    .padding(.top, OMTheme.Spacing.s2)
            }
        } else {
            OMCard { OMG5StateView(state: .empty, message: "这周还没有日程数据。") }
        }
    }

    private var weekSwitcher: some View {
        OMCard(tight: true) {
            HStack(spacing: 0) {
                weekArrow("chevron.left", enabled: model.week > 1) { model.week -= 1 }
                Spacer()
                VStack(spacing: 2) {
                    Text("第 \(model.week) 周")
                        .font(OMTheme.TypeToken.callout.weight(.bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                    if case let .loaded(data) = model.phase, let range = Self.rangeLabel(data.weekStart) {
                        Text(range)
                            .font(OMTheme.TypeToken.caption)
                            .foregroundStyle(OMTheme.ColorToken.mist)
                    }
                }
                Spacer()
                if let current = model.currentWeek, current != model.week {
                    Button("本周") { model.week = current }
                        .font(OMTheme.TypeToken.caption.weight(.bold))
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.horizontal, 10)
                        .frame(height: 30)
                        .background(OMTheme.ColorToken.yolk)
                        .clipShape(Capsule())
                        .padding(.trailing, 6)
                }
                weekArrow("chevron.right", enabled: model.week < 30) { model.week += 1 }
            }
        }
    }

    private func weekArrow(_ systemName: String, enabled: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(enabled ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist.opacity(0.4))
                .frame(width: 36, height: 36)
                .background(OMTheme.ColorToken.paper)
                .clipShape(Circle())
                .overlay { Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth) }
        }
        .buttonStyle(OMButtonPressStyle())
        .disabled(!enabled)
    }

    private var legend: some View {
        HStack(spacing: 14) {
            legendDot(OMTheme.ColorToken.card, border: OMTheme.ColorToken.line, label: "课程")
            legendDot(OMTheme.ColorToken.yolk, border: OMTheme.ColorToken.yolkBorder, label: "约局")
            Spacer()
            HStack(spacing: 3) {
                Image(systemName: "chevron.left")
                Text("滑动看更多天")
                Image(systemName: "chevron.right")
            }
            .font(OMTheme.TypeToken.caption)
            .foregroundStyle(OMTheme.ColorToken.mist)
        }
        .padding(.vertical, OMTheme.Spacing.s2)
    }

    private func legendDot(_ fill: Color, border: Color, label: String) -> some View {
        HStack(spacing: 5) {
            RoundedRectangle(cornerRadius: 3)
                .fill(fill)
                .frame(width: 12, height: 12)
                .overlay { RoundedRectangle(cornerRadius: 3).stroke(border, lineWidth: 1) }
            Text(label)
                .font(OMTheme.TypeToken.caption)
                .foregroundStyle(OMTheme.ColorToken.mist)
        }
    }

    private static func rangeLabel(_ weekStart: Date?) -> String? {
        guard let weekStart else { return nil }
        let formatter = DateFormatter()
        formatter.locale = Locale(identifier: "zh_CN")
        formatter.dateFormat = "M/d"
        let end = Calendar.current.date(byAdding: .day, value: 6, to: weekStart)!
        return "\(formatter.string(from: weekStart)) – \(formatter.string(from: end))"
    }
}

/// 时间轴日程网格：只显示 3 天窗口，头部即窗口内 3 天，左右横滑逐天平移，滑过周界自动切周。
private struct WeekScheduleGrid: View {
    let weekStart: Date
    let blocks: [ScheduleBlock]
    @Binding var windowStart: Int
    /// 滑出本周边界时回调（+1 下一周 / -1 上一周）。
    let onOverflow: (Int) -> Void
    let onTap: (ScheduleBlock) -> Void

    private static let hourHeight: CGFloat = 34
    private static let gutter: CGFloat = 24
    private static let visibleDays = 3
    private static let maxWindowStart = 7 - visibleDays

    private var calendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.firstWeekday = 2
        return calendar
    }

    /// 窗口内可见的块。
    private var visibleBlocks: [ScheduleBlock] {
        guard let lower = calendar.date(byAdding: .day, value: windowStart, to: weekStart),
              let upper = calendar.date(byAdding: .day, value: Self.visibleDays, to: lower) else { return [] }
        return blocks.filter { $0.start >= lower && $0.start < upper }
    }

    /// 小时范围贴合窗口内事件，不再硬撑到 22 点导致整列过长；无事件时默认 8–18。
    private var hours: ClosedRange<Int> {
        guard !visibleBlocks.isEmpty else { return 8...18 }
        var lower = 24, upper = 0
        for block in visibleBlocks {
            lower = min(lower, calendar.component(.hour, from: block.start))
            let endHour = calendar.component(.hour, from: block.end)
            let endMinute = calendar.component(.minute, from: block.end)
            upper = max(upper, endMinute > 0 ? endHour + 1 : endHour)
        }
        return max(0, lower)...min(24, max(upper, lower + 1))
    }

    var body: some View {
        VStack(spacing: OMTheme.Spacing.s2) {
            dayHeader
            timeGrid
        }
        .contentShape(Rectangle())
        .gesture(swipeGesture)
    }

    /// 窗口内 3 天的列头：与网格列对齐，今天用黄圆强调。
    private var dayHeader: some View {
        GeometryReader { proxy in
            let columnWidth = (proxy.size.width - Self.gutter) / CGFloat(Self.visibleDays)
            HStack(spacing: 0) {
                Color.clear.frame(width: Self.gutter, height: 1)
                ForEach(0..<Self.visibleDays, id: \.self) { column in
                    let offset = windowStart + column
                    let day = calendar.date(byAdding: .day, value: offset, to: weekStart)!
                    let isToday = calendar.isDateInToday(day)
                    HStack(spacing: 7) {
                        Text("\(calendar.component(.day, from: day))")
                            .font(OMTheme.TypeToken.mono(.callout, weight: .bold))
                            .foregroundStyle(OMTheme.ColorToken.ink)
                            .frame(width: 32, height: 32)
                            .background(isToday ? OMTheme.ColorToken.yolk : OMTheme.ColorToken.paper)
                            .clipShape(Circle())
                            .overlay {
                                if !isToday {
                                    Circle().stroke(OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                                }
                            }
                        Text(isToday ? "今天" : "周\(Self.weekdaySymbols[offset])")
                            .font(OMTheme.TypeToken.footnote.weight(isToday ? .bold : .semibold))
                            .foregroundStyle(isToday ? OMTheme.ColorToken.ink : OMTheme.ColorToken.mist)
                    }
                    .frame(width: columnWidth)
                }
            }
        }
        .frame(height: 36)
        .animation(OMTheme.Motion.medium, value: windowStart)
    }

    /// 左右横滑逐天平移；滑到周界继续滑则切上/下一周。
    private var swipeGesture: some Gesture {
        DragGesture(minimumDistance: 25)
            .onEnded { value in
                guard abs(value.translation.width) > abs(value.translation.height) * 1.4 else { return }
                let step = value.translation.width < 0 ? 1 : -1
                let next = windowStart + step
                if next < 0 {
                    onOverflow(-1)
                } else if next > Self.maxWindowStart {
                    onOverflow(1)
                } else {
                    withAnimation(OMTheme.Motion.medium) { windowStart = next }
                }
            }
    }

    private var timeGrid: some View {
        let hourCount = hours.upperBound - hours.lowerBound
        let totalHeight = CGFloat(hourCount) * Self.hourHeight
        return GeometryReader { proxy in
            let columnWidth = (proxy.size.width - Self.gutter) / CGFloat(Self.visibleDays)
            ZStack(alignment: .topLeading) {
                // 小时横线 + 刻度
                ForEach(0...hourCount, id: \.self) { index in
                    let y = CGFloat(index) * Self.hourHeight
                    Rectangle()
                        .fill(OMTheme.ColorToken.line.opacity(index == 0 || index == hourCount ? 0.9 : 0.55))
                        .frame(width: proxy.size.width - Self.gutter, height: 1)
                        .offset(x: Self.gutter, y: y)
                    if index < hourCount {
                        Text("\(hours.lowerBound + index)")
                            .font(OMTheme.TypeToken.mono(.caption2, weight: .semibold))
                            .foregroundStyle(OMTheme.ColorToken.mist)
                            .frame(width: Self.gutter - 6, alignment: .trailing)
                            .offset(y: y - 5)
                    }
                }
                // 列分隔线
                ForEach(1..<Self.visibleDays, id: \.self) { column in
                    Rectangle()
                        .fill(OMTheme.ColorToken.line.opacity(0.35))
                        .frame(width: 1, height: totalHeight)
                        .offset(x: Self.gutter + CGFloat(column) * columnWidth)
                }
                // 今天列淡黄底
                if let todayColumn = todayColumnIndex {
                    Rectangle()
                        .fill(OMTheme.ColorToken.yolk.opacity(0.08))
                        .frame(width: columnWidth, height: totalHeight)
                        .offset(x: Self.gutter + CGFloat(todayColumn) * columnWidth)
                }
                // 事件块
                ForEach(placedBlocks(columnWidth: columnWidth), id: \.block.id) { placed in
                    blockView(placed.block)
                        .frame(width: placed.width, height: placed.height)
                        .offset(x: placed.x, y: placed.y)
                }
            }
        }
        .frame(height: totalHeight)
        .animation(OMTheme.Motion.medium, value: windowStart)
    }

    private var todayColumnIndex: Int? {
        let index = calendar.dateComponents([.day], from: weekStart, to: calendar.startOfDay(for: Date())).day ?? -1
        guard (0..<7).contains(index) else { return nil }
        let column = index - windowStart
        return (0..<Self.visibleDays).contains(column) ? column : nil
    }

    private func blockView(_ block: ScheduleBlock) -> some View {
        let past = block.end < Date()
        return Button { onTap(block) } label: {
            VStack(alignment: .leading, spacing: 2) {
                Text(Self.gridTitle(block.title))
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .lineLimit(2)
                    .minimumScaleFactor(0.85)
                    .multilineTextAlignment(.leading)
                Text(Self.timeRangeLabel(start: block.start, end: block.end))
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(OMTheme.ColorToken.ink.opacity(block.isGathering ? 0.72 : 0.55))
                    .lineLimit(1)
                    .monospacedDigit()
                if let detail = block.detail, !detail.isEmpty {
                    Text(Self.shortLocation(detail))
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(OMTheme.ColorToken.ink.opacity(0.62))
                        .lineLimit(1)
                        .multilineTextAlignment(.leading)
                }
                Spacer(minLength: 0)
            }
            .padding(4)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(block.isGathering ? OMTheme.ColorToken.yolk.opacity(0.92) : OMTheme.ColorToken.card)
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .overlay {
                RoundedRectangle(cornerRadius: 6)
                    .stroke(
                        block.isGathering
                            ? OMTheme.ColorToken.yolkBorder
                            : (block.isChangedCourse ? OMTheme.ColorToken.yolkBorder : OMTheme.ColorToken.line),
                        lineWidth: 1
                    )
            }
            .opacity(past ? 0.55 : 1)
        }
        .buttonStyle(OMButtonPressStyle())
    }

    /// 周历格子空间有限：去掉「本 (专必)」这类修读类别前缀。
    private static func gridTitle(_ value: String) -> String {
        var text = value.trimmingCharacters(in: .whitespaces)
        if let range = text.range(of: #"^本?\s*[\(（][^\)）]{1,6}[\)）]\s*"#, options: .regularExpression) {
            let stripped = String(text[range.upperBound...]).trimmingCharacters(in: .whitespaces)
            if !stripped.isEmpty { text = stripped }
        }
        return text
    }

    /// 格子内时间标：10:00–11:30（等宽数字，便于扫视）。
    private static func timeRangeLabel(start: Date, end: Date) -> String {
        let style = Date.FormatStyle().hour(.defaultDigits(amPM: .omitted)).minute()
        return "\(start.formatted(style))–\(end.formatted(style))"
    }

    private struct PlacedBlock {
        let block: ScheduleBlock
        let x: CGFloat
        let y: CGFloat
        let width: CGFloat
        let height: CGFloat
    }

    /// 按天布块：重叠簇内分道并排，其余全宽。
    private func placedBlocks(columnWidth: CGFloat) -> [PlacedBlock] {
        var result: [PlacedBlock] = []
        let dayStartHour = hours.lowerBound
        for column in 0..<Self.visibleDays {
            let offset = windowStart + column
            guard let dayStart = calendar.date(byAdding: .day, value: offset, to: weekStart) else { continue }
            let dayEnd = calendar.date(byAdding: .day, value: 1, to: dayStart)!
            let dayBlocks = blocks
                .filter { $0.start >= dayStart && $0.start < dayEnd }
                .sorted { $0.start < $1.start }
            guard !dayBlocks.isEmpty else { continue }

            // 重叠簇切分
            var clusters: [[ScheduleBlock]] = []
            var current: [ScheduleBlock] = []
            var clusterEnd = Date.distantPast
            for block in dayBlocks {
                if current.isEmpty || block.start < clusterEnd {
                    current.append(block)
                    clusterEnd = max(clusterEnd, block.end)
                } else {
                    clusters.append(current)
                    current = [block]
                    clusterEnd = block.end
                }
            }
            if !current.isEmpty { clusters.append(current) }

            let columnX = Self.gutter + CGFloat(column) * columnWidth
            for cluster in clusters {
                // 簇内贪心分道
                var laneEnds: [Date] = []
                var laneAssignment: [(ScheduleBlock, Int)] = []
                for block in cluster {
                    if let lane = laneEnds.firstIndex(where: { $0 <= block.start }) {
                        laneEnds[lane] = block.end
                        laneAssignment.append((block, lane))
                    } else {
                        laneEnds.append(block.end)
                        laneAssignment.append((block, laneEnds.count - 1))
                    }
                }
                let laneCount = laneEnds.count
                let laneWidth = (columnWidth - 3) / CGFloat(laneCount)
                for (block, lane) in laneAssignment {
                    let startMinutes = minutes(of: block.start, sinceHour: dayStartHour, dayStart: dayStart)
                    let endMinutes = minutes(of: min(block.end, dayEnd), sinceHour: dayStartHour, dayStart: dayStart)
                    let y = max(0, CGFloat(startMinutes) / 60 * Self.hourHeight)
                    let height = max(20, CGFloat(endMinutes - startMinutes) / 60 * Self.hourHeight - 2)
                    result.append(PlacedBlock(
                        block: block,
                        x: columnX + 1.5 + CGFloat(lane) * laneWidth,
                        y: y + 1,
                        width: laneWidth - 1.5,
                        height: height
                    ))
                }
            }
        }
        return result
    }

    private func minutes(of date: Date, sinceHour hour: Int, dayStart: Date) -> Int {
        let total = calendar.dateComponents([.minute], from: dayStart, to: date).minute ?? 0
        return total - hour * 60
    }

    /// 「珠海校区-教学大楼-珠海 E301」→「E301」这类短显示。
    private static func shortLocation(_ value: String) -> String {
        let parts = value.components(separatedBy: CharacterSet(charactersIn: "-—"))
        if let last = parts.last?.trimmingCharacters(in: .whitespaces), !last.isEmpty, parts.count > 1 {
            return last
        }
        return value
    }

    private static let weekdaySymbols = ["一", "二", "三", "四", "五", "六", "日"]
}

@MainActor private final class CourseDetailModel: ObservableObject {
    enum Phase { case loading, loaded(CampusCourseDetail), failed(String) }
    @Published var phase: Phase = .loading
    let id: String; let repository: TodayRepository
    init(id: String, repository: TodayRepository) { self.id = id; self.repository = repository }
    func load() async { do { phase = .loaded(try await repository.course(id)) } catch { phase = .failed(error.localizedDescription) } }
}

/// B3.1 · 课程详情
private struct CourseDetailView: View {
    @StateObject private var model: CourseDetailModel
    @EnvironmentObject private var router: AppRouter
    @Environment(\.dismiss) private var dismiss
    init(id: String, repository: TodayRepository) { _model = StateObject(wrappedValue: CourseDetailModel(id: id, repository: repository)) }
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "课程", title: "课程详情", lulu: .homeThinking)
                    switch model.phase {
                    case .loading:
                        OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                    case let .failed(message):
                        OMCard {
                            OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                                Task { await model.load() }
                            }
                        }
                    case let .loaded(value):
                        OMCard {
                            OMTextRole.t2(value.name)
                            OMTextRole.foot(Self.courseMetaLine(value))
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMCard {
                            OMTextRole.t3("能力来源")
                            OMFlowLayout {
                                ForEach(value.capabilityTags, id: \.self) { OMChip(text: $0, kind: .solid) }
                            }
                            .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMButton("和同课的人开个冲刺局", systemIcon: "person.3") {
                            dismiss()
                            router.push(.intentPreset(.courseDDL))
                        }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } } }
            .task { await model.load() }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B3.1-course-detail")
        }
    }

    private static func courseMetaLine(_ value: CampusCourseDetail) -> String {
        let parts = [value.code, value.classCode, value.term]
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty && !Timetable.Entry.isTechnicalCode($0) }
        return parts.isEmpty ? value.term : parts.joined(separator: " · ")
    }
}

@MainActor private final class AssignmentsViewModel: ObservableObject {
    enum Phase { case loading, loaded([CampusAssignment]), failed(String) }
    @Published var phase: Phase = .loading
    let repository: TodayRepository
    init(repository: TodayRepository) { self.repository = repository }
    func load() async { do { phase = .loaded(try await repository.assignments()) } catch { phase = .failed(error.localizedDescription) } }
}

/// B4 · 未完成作业
struct AssignmentsView: View {
    @StateObject private var model: AssignmentsViewModel
    @State private var selected: CampusAssignment?
    @EnvironmentObject private var router: AppRouter
    private let repository: TodayRepository
    init(repository: TodayRepository) { self.repository = repository; _model = StateObject(wrappedValue: AssignmentsViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "截止在即", title: "未完成作业", lulu: .homeThinking)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(items):
                    if items.isEmpty {
                        OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                    }
                    ForEach(items) { item in
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("homework-pencil.png", size: .s44)
                                VStack(alignment: .leading, spacing: 3) {
                                    OMTextRole.t3(item.title)
                                    Text(item.dueAt.formatted(date: .abbreviated, time: .shortened))
                                        .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                                        .foregroundStyle(OMTheme.ColorToken.ink)
                                }
                                Spacer()
                            }
                        }
                        .contentShape(Rectangle())
                        .onTapGesture { selected = item }
                    }
                }
                OMButton("开一个 DDL 冲刺局", systemIcon: "timer") {
                    router.push(.intentPreset(.courseDDL))
                }
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("assignments-create-ddl-intent")
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .sheet(item: $selected) { item in AssignmentDetailView(item: item, repository: repository) }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B4-assignments")
    }
}

/// B4.1 · 作业详情
private struct AssignmentDetailView: View {
    let item: CampusAssignment
    let repository: TodayRepository
    @EnvironmentObject private var router: AppRouter
    @Environment(\.dismiss) private var dismiss
    @State private var detail: CampusAssignmentDetail?
    @State private var error: String?
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "作业", title: detail?.title ?? item.title, lulu: .homeThinking)
                    if let detail {
                        OMCard {
                            OMTextRole.t3(detail.course.map { "\($0.code) · \($0.name)" } ?? "课程来源待同步")
                            Text("截止 \(detail.dueAt.formatted(date: .abbreviated, time: .shortened))")
                                .font(OMTheme.TypeToken.mono(.footnote, weight: .bold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMButton("开一个 DDL 冲刺局", systemIcon: "timer") {
                            dismiss()
                            router.push(.intentPreset(.courseDDL))
                        }
                    } else if let error {
                        OMCard { OMG5StateView(state: .networkError, message: error) }
                    } else {
                        OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } } }
            .task {
                do { detail = try await repository.assignment(item.id) }
                catch { self.error = error.localizedDescription }
            }
            .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B4.1-assignment-detail")
        }
    }
}

enum VenueToolKind: String { case room, gym }

@MainActor private final class VenueToolViewModel: ObservableObject {
    @Published var date = Date().addingTimeInterval(86_400)
    @Published var category: String
    @Published var resource = ""
    @Published var start = "19:00"
    @Published var end = "21:00"
    @Published var result: JSONValue?
    @Published var working = false
    @Published var error: String?
    let kind: VenueToolKind; let repository: TodayRepository
    init(kind: VenueToolKind, repository: TodayRepository) { self.kind = kind; self.repository = repository; category = kind == .room ? "15" : "羽毛球" }
    func query() async {
        guard !working else { return }; working = true; error = nil; defer { working = false }
        do { result = try await (kind == .room ? repository.roomAvailability(kind: category, date: date) : repository.gymAvailability(venueType: category, date: date)) }
        catch { self.error = error.localizedDescription }
    }
    var preview: CampusPreviewRequest? {
        guard !resource.trimmingCharacters(in: .whitespaces).isEmpty, start < end else { return nil }
        let dateText = CampusDayCodec.string(from: date)
        if kind == .room {
            return .init(action: "room.reserve_preview", params: ["kind": .string(category), "room": .string(resource), "date": .string(dateText), "start": .string(start), "end": .string(end), "members": .array([]), "services": .array([])])
        }
        return .init(action: "gym.book_preview", params: ["venue_type": .string(category), "venue": .string(resource), "date": .string(dateText), "start": .string(start), "end": .string(end)])
    }
}

/// B5 / B6 · 场馆与研讨室
struct VenueToolView: View {
    @StateObject private var model: VenueToolViewModel
    @EnvironmentObject private var environment: AppEnvironment
    @EnvironmentObject private var router: AppRouter
    @State private var preview: CampusPreviewRequest?
    init(kind: VenueToolKind, repository: TodayRepository) { _model = StateObject(wrappedValue: VenueToolViewModel(kind: kind, repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(
                    eyebrow: model.kind == .room ? "可预约空间" : "运动场地",
                    title: model.kind == .room ? "图书馆研讨室" : "体育场馆",
                    lulu: .homeIdle
                )
                OMCard {
                    TextField(model.kind == .room ? "房型（如 15）" : "项目（如 羽毛球）", text: $model.category)
                        .omInputStyle()
                    DatePicker("日期", selection: $model.date, displayedComponents: .date)
                        .font(OMTheme.TypeToken.callout)
                        .tint(OMTheme.ColorToken.ink)
                        .padding(.top, OMTheme.Spacing.s3)
                        .environment(\.timeZone, CampusDayCodec.timeZone)
                    OMButton(
                        "查询实时空档", systemIcon: "magnifyingglass", loading: model.working,
                        disabledReason: model.category.isEmpty ? "填写类型" : nil
                    ) { Task { await model.query() } }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                ReferenceVenueDirectory(kind: model.kind, resource: $model.resource)
                if let error = model.error {
                    OMCard {
                        OMG5StateView(state: .networkError, message: error, actionTitle: "重试") {
                            Task { await model.query() }
                        }
                    }
                }
                if let result = model.result {
                    StructuredResultCard(title: "服务端空档", value: result)
                }
                OMCard {
                    OMTextRole.t3("选择时段并生成预览")
                    TextField(model.kind == .room ? "研讨室编号" : "场馆名称", text: $model.resource)
                        .omInputStyle()
                        .padding(.top, OMTheme.Spacing.s3)
                    HStack(spacing: 8) {
                        TextField("开始 HH:mm", text: $model.start).omInputStyle()
                        TextField("结束 HH:mm", text: $model.end).omInputStyle()
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                    OMButton("进入个人行动预览", systemIcon: "doc.text.magnifyingglass", disabledReason: model.preview == nil ? "填写资源与有效时段" : nil) {
                        preview = model.preview
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                if model.kind == .gym {
                    OMButton("用这个时段找运动搭子", systemIcon: "person.2.fill") {
                        router.push(.intentPreset(.sport))
                    }
                    .accessibilityIdentifier("gym-find-sport-partner")
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .sheet(item: $preview) { request in
            PersonalActionPreviewView(action: request.action, params: request.params, repository: environment.actions)
        }
        .accessibilityIdentifier(model.kind == .room ? "screen-B6-room" : "screen-B5-gym")
    }
}

private struct ReferenceVenueDirectory: View {
    let kind: VenueToolKind
    @Binding var resource: String
    @EnvironmentObject private var environment: AppEnvironment
    @State private var campusID = "guangzhou_south"
    @State private var searchText = ""
    @State private var venues: [ReferenceVenue] = []
    @State private var places: [ReferencePlace] = []
    @State private var campuses: [ReferenceCampus] = []
    @State private var bundleVersion: String?
    @State private var error: String?

    var body: some View {
        OMCard {
            HStack {
                OMTextRole.t3("离线版本化目录")
                Spacer()
                Text(bundleVersion ?? "校验中")
                    .font(OMTheme.TypeToken.mono(.caption))
                    .foregroundStyle(OMTheme.ColorToken.mist)
            }
            Picker("校区", selection: $campusID) {
                ForEach(campuses) { Text($0.name).tag($0.id) }
            }
            .font(OMTheme.TypeToken.callout)
            .tint(OMTheme.ColorToken.ink)
            .padding(.top, OMTheme.Spacing.s2)
            TextField("搜索官方地点或中文别名", text: $searchText)
                .omInputStyle()
                .padding(.top, OMTheme.Spacing.s2)
                .accessibilityIdentifier("reference-place-search")
            if !places.isEmpty {
                ForEach(places.prefix(5)) { place in
                    Button {
                        resource = place.name
                    } label: {
                        HStack {
                            VStack(alignment: .leading) {
                                Text(place.name).font(OMTheme.TypeToken.callout.weight(.semibold))
                                Text(place.location)
                                    .font(OMTheme.TypeToken.footnote)
                                    .foregroundStyle(OMTheme.ColorToken.mist)
                            }
                            Spacer()
                            Image(systemName: "arrow.down.to.line").foregroundStyle(OMTheme.ColorToken.sage)
                        }
                        .padding(.vertical, 8)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                }
            }
            ForEach(filteredVenues.prefix(8)) { venue in
                Button {
                    resource = venue.name
                } label: {
                    HStack {
                        Text(venue.name).font(OMTheme.TypeToken.callout)
                        Spacer()
                        if let capacity = venue.capacity {
                            Text("\(capacity) 人")
                                .font(OMTheme.TypeToken.footnote)
                                .foregroundStyle(OMTheme.ColorToken.mist)
                        }
                    }
                    .padding(.vertical, 8)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
            }
            if let error {
                OMTextRole.foot("离线目录整包不可用：\(error)")
                    .padding(.top, OMTheme.Spacing.s2)
            }
        }
        .accessibilityIdentifier("reference-venue-directory")
        .task(id: campusID) { await loadDirectory() }
        .task(id: searchText) { await searchPlaces() }
    }

    private var filteredVenues: [ReferenceVenue] {
        let tokens = kind == .room
            ? ["classroom", "meeting", "seminar", "library", "room"]
            : ["gym", "sport", "badminton", "stadium", "court", "field"]
        let matched = venues.filter { venue in
            tokens.contains { venue.type.lowercased().contains($0) }
                || (kind == .room && venue.name.contains("室"))
                || (kind == .gym && ["体育", "球", "场", "馆"].contains { venue.name.contains($0) })
        }
        return matched.isEmpty ? venues : matched
    }

    @MainActor private func loadDirectory() async {
        do {
            try await environment.referenceData.ensureReady()
            campuses = await environment.referenceData.campusDirectory()
            venues = await environment.referenceData.venueDirectory(campusID: campusID)
            bundleVersion = await environment.referenceData.bundleVersion
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    @MainActor private func searchPlaces() async {
        places = await environment.referenceData.search(searchText)
            .filter { $0.campusID == campusID }
    }
}

/// B9 · 班车查询（离线时刻表，数据见 CampusBusSchedule）
struct CampusTransitReferenceView: View {
    @EnvironmentObject private var environment: AppEnvironment
    @State private var fromCampus = "东校园"
    @State private var toCampus = "北校园"
    @State private var dayKind = CampusBusSchedule.dayKind()
    @State private var sectionNumber = 1
    @State private var sectionTimes: (String, String)?

    init(repository: TodayRepository) {}

    private static let campuses = ["东校园", "南校园", "北校园", "珠海校区"]

    private var route: CampusBusSchedule.Route? {
        CampusBusSchedule.routes.first { $0.from == fromCampus && $0.to == toCampus }
    }
    private var isTodayKind: Bool { dayKind == CampusBusSchedule.dayKind() }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "跨校区", title: "班车", lulu: .homeIdle)

                OMCard {
                    HStack(spacing: 10) {
                        OMTextRole.t3("从")
                            .frame(width: 20, alignment: .leading)
                        OMSeg(items: Self.campuses, label: { $0.replacingOccurrences(of: "校园", with: "").replacingOccurrences(of: "校区", with: "") }, selection: $fromCampus)
                    }
                    HStack(spacing: 10) {
                        OMTextRole.t3("到")
                            .frame(width: 20, alignment: .leading)
                        OMSeg(items: Self.campuses, label: { $0.replacingOccurrences(of: "校园", with: "").replacingOccurrences(of: "校区", with: "") }, selection: $toCampus)
                    }
                    .padding(.top, OMTheme.Spacing.s2)
                }
                .accessibilityIdentifier("transit-campus-picker")

                OMSeg(items: CampusBusSchedule.DayKind.allCases, label: \.rawValue, selection: $dayKind)
                    .padding(.bottom, OMTheme.Spacing.s3)

                if fromCampus == toCampus {
                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker("school-bus.png", size: .s44)
                            OMTextRole.foot("选两个不同的校区就能查班次。")
                            Spacer()
                        }
                    }
                } else if let route {
                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker("school-bus.png", size: .s44)
                            VStack(alignment: .leading, spacing: 2) {
                                OMTextRole.t3(route.title)
                                OMTextRole.foot("\(route.fromStation) → \(route.toStation)")
                            }
                            Spacer()
                        }
                        if route.isQiguan {
                            OMTextRole.foot("岐关公路班线 · ¥40 · 约 100 分钟，需在岐关小程序购票。")
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                        OMDivider()
                        let departures = route.departures(dayKind)
                        if departures.isEmpty {
                            HStack(spacing: 10) {
                                OMSticker("school-bus.png", size: .s44)
                                OMTextRole.foot("节假日这个方向没有班车，换工作日看看。")
                                Spacer()
                            }
                        } else {
                            let next = isTodayKind ? CampusBusSchedule.nextDeparture(on: route, kind: dayKind) : nil
                            ForEach(Array(departures.enumerated()), id: \.offset) { _, dep in
                                HStack(spacing: 10) {
                                    Text(dep.time)
                                        .font(OMTheme.TypeToken.callout.weight(.bold))
                                        .foregroundStyle(OMTheme.ColorToken.ink)
                                        .frame(width: 52, alignment: .leading)
                                    if let arrive = dep.arrive {
                                        Text("→ \(arrive)")
                                            .font(OMTheme.TypeToken.footnote)
                                            .foregroundStyle(OMTheme.ColorToken.mist)
                                    }
                                    if let via = dep.via {
                                        Text(via)
                                            .font(OMTheme.TypeToken.footnote)
                                            .foregroundStyle(OMTheme.ColorToken.mist)
                                            .lineLimit(1)
                                    }
                                    Spacer()
                                    if route.isQiguan {
                                        OMChip(text: dep.express ? "直达" : "经停", kind: .soft)
                                    }
                                    if dep.staffOnly {
                                        OMChip(text: "教职工", kind: .soft)
                                    }
                                    if let next, next.time == dep.time {
                                        OMChip(text: "下一班", kind: .gap)
                                    }
                                }
                                .padding(.vertical, 7)
                            }
                        }
                    }
                    .accessibilityIdentifier("transit-schedule-card")
                } else {
                    OMCard {
                        HStack(spacing: 10) {
                            OMSticker("school-bus.png", size: .s44)
                            OMTextRole.foot("这两个校区之间没有直达班车。去珠海校区可从南校园或东校园坐岐关车。")
                            Spacer()
                        }
                    }
                    .accessibilityIdentifier("transit-schedule-card")
                }

                OMSection(title: "节次时间")
                OMCard {
                    OMStepperRow(title: "第几节", value: $sectionNumber, range: 1...11, unit: "节")
                    if let sectionTimes {
                        OMDivider()
                        HStack {
                            OMTextRole.t3("第 \(sectionNumber) 节")
                            Spacer()
                            Text("\(sectionTimes.0) – \(sectionTimes.1)")
                                .font(OMTheme.TypeToken.callout.weight(.semibold))
                                .foregroundStyle(OMTheme.ColorToken.ink)
                        }
                    }
                }
                .accessibilityIdentifier("reference-transit-section-card")
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task(id: sectionNumber) {
            try? await environment.referenceData.ensureReady()
            sectionTimes = await environment.referenceData.section(sectionNumber)
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B9-transit-reference")
    }
}

/// B7 · 校园活动
struct CampusEventsView: View {
    @StateObject private var model: GuestEventsViewModel
    init(repository: CampusEventRepository) { _model = StateObject(wrappedValue: GuestEventsViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "官方活动", title: "校园活动", lulu: .coreCelebrate)
                CampusEventsContent(model: model)
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B7-events")
    }
}

/// 校园活动列表内容：B7 页面与「活动」Tab 分段共用。
struct CampusEventsContent: View {
    @ObservedObject var model: GuestEventsViewModel
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    @State private var selected: CampusEvent?
    @State private var showsPublisher = false
    @State private var typeFilter: String? = nil

    var body: some View {
        switch model.phase {
        case .loading:
            OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
        case let .failed(message):
            OMCard {
                OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                    Task { await model.load(force: true) }
                }
            }
        case let .loaded(items):
            if items.isEmpty {
                OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
            }
            let types = items.reduce(into: [String]()) { acc, item in
                if !acc.contains(item.displayType) { acc.append(item.displayType) }
            }
            if types.count >= 2 {
                typeFilterRow(types)
                    .padding(.bottom, OMTheme.Spacing.s3)
            }
            let visible = typeFilter.map { f in items.filter { $0.displayType == f } } ?? items
            if visible.isEmpty {
                OMCard { OMG5StateView(state: .empty, message: "这个分类暂时没有活动。") }
            }
            ForEach(visible) { item in
                OMCard {
                    HStack {
                        OMChip(text: item.displayType, kind: .soft)
                        if item.details["publisher"]?.stringValue == "user" {
                            OMChip(text: "同学发布", kind: .standard)
                        }
                        Spacer()
                    }
                    OMTextRole.t3(item.title).padding(.top, OMTheme.Spacing.s2)
                    Text(item.startsAt?.formatted(date: .abbreviated, time: .shortened) ?? "时间待官方确认")
                        .font(OMTheme.TypeToken.callout)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .padding(.top, 4)
                    OMTextRole.foot(item.location ?? "地点待官方确认").padding(.top, 2)
                }
                .contentShape(Rectangle())
                .onTapGesture { selected = item }
            }
        }
        HStack(spacing: 8) {
            OMButton("找活动同行", systemIcon: "person.2", kind: .ghost, small: true) {
                router.push(.intentPreset(.event))
            }
            .accessibilityIdentifier("events-create-companion-intent")
            OMButton("发布活动", systemIcon: "plus", kind: .ghost, small: true) {
                showsPublisher = true
            }
            .accessibilityIdentifier("events-publish-entry")
        }
        .padding(.top, OMTheme.Spacing.s2)
        .sheet(item: $selected) { item in
            CampusEventDetailSheet(item: item) {
                selected = nil
                router.push(.intentPreset(.event))
            }
        }
        .sheet(isPresented: $showsPublisher) {
            CampusEventPublishView(events: environment.campusEvents, social: environment.social) {
                Task { await model.load(force: true) }
            }
        }
        .task {
            #if DEBUG
            // 截图取证：-EventDetailID <id> 自动打开详情 sheet（id 缺省取第一条）。
            let args = ProcessInfo.processInfo.arguments
            guard let i = args.firstIndex(of: "-EventDetailID"), args.indices.contains(i + 1) else { return }
            for _ in 0..<20 {
                try? await Task.sleep(nanoseconds: 300_000_000)
                if case let .loaded(items) = model.phase, !items.isEmpty {
                    selected = items.first { $0.id == args[i + 1] } ?? items.first
                    return
                }
            }
            #endif
        }
    }

    /// 类型筛选：横滑 chip 行，选中态墨底，再点取消。
    private func typeFilterRow(_ types: [String]) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                filterChip("全部", selected: typeFilter == nil) { typeFilter = nil }
                ForEach(types, id: \.self) { type in
                    filterChip(type, selected: typeFilter == type) {
                        typeFilter = (typeFilter == type) ? nil : type
                    }
                }
            }
        }
        .accessibilityIdentifier("events-type-filter")
    }

    private func filterChip(_ title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(OMTheme.TypeToken.footnote.weight(.semibold))
                .foregroundStyle(selected ? OMTheme.ColorToken.card : OMTheme.ColorToken.ink)
                .padding(.horizontal, 14)
                .frame(minHeight: 32)
                .background(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.card)
                .clipShape(Capsule())
                .overlay {
                    Capsule().stroke(selected ? OMTheme.ColorToken.ink : OMTheme.ColorToken.line, lineWidth: OMTheme.Radius.borderWidth)
                }
        }
        .buttonStyle(.plain)
    }
}

/// B7.1 · 活动详情 sheet：信息图标行 + 说明 + 行动，medium detent 避免半屏空白。
struct CampusEventDetailSheet: View {
    let item: CampusEvent
    let onFindCompanion: () -> Void

    @Environment(\.openURL) private var openURL
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    HStack {
                        OMChip(text: item.displayType, kind: .soft)
                        if item.details["publisher"]?.stringValue == "user" {
                            OMChip(text: "同学发布", kind: .standard)
                        }
                        Spacer()
                    }
                    Text(item.title)
                        .font(OMTheme.TypeToken.title2)
                        .foregroundStyle(OMTheme.ColorToken.ink)
                        .fixedSize(horizontal: false, vertical: true)
                        .padding(.top, OMTheme.Spacing.s2)
                    OMCard {
                        infoRow(icon: "calendar", text: timeText)
                        if let location = item.location, !location.isEmpty {
                            infoRow(icon: "mappin", text: location)
                        }
                        if let organizer = item.details["organizer"]?.stringValue, !organizer.isEmpty {
                            infoRow(icon: "building.columns", text: organizer)
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                    if let description = item.details["description"]?.stringValue, !description.isEmpty {
                        OMCard {
                            OMTextRole.t3("活动说明")
                            OMTextRole.call(description)
                                .foregroundStyle(OMTheme.ColorToken.ink)
                                .padding(.top, OMTheme.Spacing.s2)
                        }
                    }
                    VStack(spacing: 10) {
                        if let url = item.officialUrl {
                            OMButton("打开官方报名页", systemIcon: "safari") { openURL(url) }
                        }
                        OMButton("找活动同行", systemIcon: "person.2", kind: item.officialUrl == nil ? .primary : .ghost) {
                            dismiss()
                            onFindCompanion()
                        }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.top, OMTheme.Spacing.s3)
                .padding(.bottom, 32)
            }
            .background(OMPageBackground())
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("关闭") { dismiss() } }
            }
        }
        .presentationDetents([.medium, .large])
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B7.1-event-detail")
    }

    private var timeText: String {
        guard let start = item.startsAt else { return "时间待官方确认" }
        let head = start.formatted(.dateTime.weekday(.wide).month().day().hour().minute())
        if let end = item.endsAt {
            return head + " — " + end.formatted(date: .omitted, time: .shortened)
        }
        return head
    }

    private func infoRow(icon: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(OMTheme.ColorToken.mist)
                .frame(width: 18)
            Text(text)
                .font(OMTheme.TypeToken.callout)
                .foregroundStyle(OMTheme.ColorToken.ink)
                .fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 0)
        }
        .padding(.top, OMTheme.Spacing.s2)
    }
}

/// B8 · 组会与课题（预置查询）
struct CampusPresetQueryView: View {
    let screenID: String
    let title: String
    let query: String
    @StateObject private var model: HermesAskViewModel
    init(screenID: String, title: String, query: String, repository: TodayRepository) { self.screenID = screenID; self.title = title; self.query = query; _model = StateObject(wrappedValue: HermesAskViewModel(repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "HERMES", title: title)
                OMCard {
                    OMTextRole.t3("数据由校园行动层实时查询")
                    OMButton("刷新查询", systemIcon: "arrow.clockwise", loading: model.working) {
                        Task { await model.ask(query) }
                    }
                    .padding(.top, OMTheme.Spacing.s3)
                }
                if let error = model.error {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                }
                if let result = model.result {
                    StructuredResultCard(title: result.cardType, value: result.data)
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { if model.result == nil { await model.ask(query) } }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-\(screenID)-campus-query")
    }
}

/// B10 · 场景触发
struct SceneTriggerDetailView: View {
    let repository: TodayRepository
    @State private var summary: TodaySummary?
    @State private var error: String?
    @State private var ignored = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "克制的场景触发", title: "场景触发", lulu: .homeListening)
                if let trigger = summary?.sceneTrigger, !ignored {
                    OMCard {
                        OMTextRole.t3(trigger.string("text") ?? "有一项校园事务可以组成短时协作局")
                        OMButton("忽略这个场景", kind: .ghost, small: true, fillsWidth: false) {
                            Task {
                                if let key = trigger.string("scene_key") {
                                    _ = try? await repository.ignoreSceneTrigger(key)
                                    ignored = true
                                }
                            }
                        }
                        .padding(.top, OMTheme.Spacing.s3)
                    }
                } else if let error {
                    OMCard { OMG5StateView(state: .networkError, message: error) }
                } else {
                    OMCard { OMG5StateView(state: .empty, message: "暂时没有内容，有进展时会告诉你。") }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task {
            do { summary = try await repository.summary(force: true) }
            catch { self.error = error.localizedDescription }
        }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-B10-scene-trigger")
    }
}

private extension Dictionary where Key == String, Value == JSONValue {
    func string(_ key: String) -> String? { if case let .string(value)? = self[key] { value } else { nil } }
}

@MainActor private final class CampusActionDetailModel: ObservableObject {
    enum Phase { case loading, loaded(CampusAction), failed(String) }
    @Published var phase: Phase = .loading
    @Published var working = false
    let id: String; let repository: ActionRepository
    init(id: String, repository: ActionRepository) { self.id = id; self.repository = repository }
    func load() async { do { phase = .loaded(try await repository.detail(id)) } catch { phase = .failed(error.localizedDescription) } }
    func authorize(_ item: CampusAction) async -> Bool {
        guard !working else { return false }; working = true; defer { working = false }
        do { phase = .loaded(try await repository.authorize(item, authorized: true)); return false }
        catch { phase = .failed(error.localizedDescription); if case APIClientError.sessionExpired = error { return true }; return false }
    }
    func execute(_ item: CampusAction) async -> Bool {
        guard !working else { return false }; working = true; defer { working = false }
        do { phase = .loaded(try await repository.execute(item)); return false }
        catch { phase = .failed(error.localizedDescription); if case APIClientError.sessionExpired = error { return true }; return false }
    }
}

/// 行动核对（深链 onemore://action/<id>）
struct CampusActionDetailView: View {
    @StateObject private var model: CampusActionDetailModel
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var router: AppRouter
    @EnvironmentObject private var environment: AppEnvironment
    init(id: String, repository: ActionRepository) { _model = StateObject(wrappedValue: CampusActionDetailModel(id: id, repository: repository)) }
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                OMHeader(eyebrow: "核对后执行", title: "行动核对", lulu: .actionExecuting)
                switch model.phase {
                case .loading:
                    OMCard { OMG5StateView(state: .loading, message: AppBrand.loadingMessage) }
                case let .failed(message):
                    OMCard {
                        OMG5StateView(state: .networkError, message: message, actionTitle: "重试") {
                            Task { await model.load() }
                        }
                    }
                case let .loaded(item):
                    if let copy = CampusActionCopy.make(
                        actionName: item.actionName,
                        params: item.params,
                        status: item.status,
                        previewSnapshot: item.previewSnapshot
                    ) {
                        CampusActionCopyCard(copy: copy)
                    } else {
                        OMCard {
                            OMTextRole.t3(item.actionName)
                            ForEach(Array(jsonRows(.object(item.params), path: "参数").enumerated()), id: \.offset) { _, row in
                                HStack(alignment: .top) {
                                    Text(row.0)
                                        .font(OMTheme.TypeToken.mono(.caption))
                                        .foregroundStyle(OMTheme.ColorToken.mist)
                                    Spacer()
                                    Text(row.1)
                                        .font(OMTheme.TypeToken.footnote)
                                        .foregroundStyle(OMTheme.ColorToken.ink)
                                        .multilineTextAlignment(.trailing)
                                }
                                .padding(.top, OMTheme.Spacing.s2)
                            }
                        }
                    }
                    if !item.isReferencePreview {
                        StructuredResultCard(title: "服务端预览快照", value: .object(item.previewSnapshot))
                        OMCard {
                            OMTextRole.t3("\(item.authorization.authorizedCount) / \(item.authorization.requiredCount) 位已核对")
                        }
                    }
                    if item.status == "succeeded" {
                        OMCard {
                            HStack(spacing: 10) {
                                OMSticker("approval-stamp.png", size: .s44)
                                OMTextRole.t3("行动已完成")
                                Spacer()
                            }
                        }
                        if item.gatheringId == nil { PersonalActionCalendarControls(item: item) }
                    } else if item.status == "failed" {
                        failedAction(item)
                    } else if item.isReferencePreview {
                        OMCard {
                            OMTextRole.t3("这是找球友的时段参考")
                            OMTextRole.foot("不是要提交的预约，不用核对。看过就可以回去了。")
                                .padding(.top, 4)
                        }
                        OMButton("知道了") {
                            Task { await environment.refreshAttention(force: true) }
                            dismiss()
                        }
                    } else if item.authorization.actorDecision != "authorized" {
                        OMButton("核对无误，分别确认", systemIcon: "checkmark.shield", loading: model.working) {
                            preserveRecovery(for: item.id)
                            Task { clearRecovery(unlessSessionExpired: await model.authorize(item)) }
                        }
                    } else if item.authorization.allAuthorized && item.gatheringId == nil {
                        OMButton("执行个人行动", systemIcon: "bolt.fill", loading: model.working) {
                            preserveRecovery(for: item.id)
                            Task { clearRecovery(unlessSessionExpired: await model.execute(item)) }
                        }
                    } else if let gatheringID = item.gatheringId {
                        OMButton("返回局内继续", systemIcon: "person.3") { router.push(.gathering(gatheringID)) }
                    } else {
                        OMButton("等待授权状态同步", disabledReason: "尚未满足服务端执行条件") {}
                    }
                }
            }
            .padding(.horizontal, OMTheme.Spacing.pageX)
            .padding(.bottom, 44)
        }
        .background(OMPageBackground())
        .task { await model.load() }
        .refreshable { await model.load() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("screen-action-detail")
    }

    @ViewBuilder private func failedAction(_ item: CampusAction) -> some View {
        let disposition = CampusActionExecutionDisposition.resolve(
            status: item.status, errorCategory: item.errorCategory
        )
        OMCard {
            HStack(spacing: 10) {
                Image(om: .warn)
                    .font(.system(size: 17))
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .frame(width: 38, height: 38)
                    .background(OMTheme.ColorToken.gapSoft)
                    .clipShape(RoundedRectangle(cornerRadius: OMTheme.Radius.small))
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("校园操作未执行")
                    OMTextRole.foot(actionFailureMessage(disposition))
                }
                Spacer()
            }
        }
        switch disposition {
        case .reauthenticate:
            OMButton("重新认证并返回此操作", icon: .scan) {
                preserveRecovery(for: item.id)
                router.recoverAfterSessionExpired(.action(item.id))
            }
        case .chooseAnotherResource, .invalidParameters:
            OMButton("重新选择参数", systemIcon: "slider.horizontal.3") {
                router.push(.formalOrScreen(CampusActionExecutionDisposition.recoveryScreen(actionName: item.actionName)))
            }
        case .retryLater, .unknownFailure:
            OMButton("刷新服务端状态", systemIcon: "arrow.clockwise", loading: model.working) {
                Task { await model.load() }
            }
            OMButton("返回校园工具", kind: .ghost) {
                router.push(.formal(.b2))
            }
            .padding(.top, OMTheme.Spacing.s2)
        case .succeeded:
            EmptyView()
        }
    }

    private func preserveRecovery(for actionID: String) {
        let route = AppRoute.action(actionID)
        router.pendingAfterAuthentication = route
        environment.recovery.saveExternalRoute(route)
    }

    private func clearRecovery(unlessSessionExpired sessionExpired: Bool) {
        guard !sessionExpired else { return }
        if case .action = router.pendingAfterAuthentication { router.pendingAfterAuthentication = nil }
        environment.recovery.clearExternalRoute()
    }
}

/// 校园活动发布（服务端 T4 信任门槛；列表匿名呈现，不显示发布者身份）。
struct CampusEventPublishView: View {
    let events: CampusEventRepository
    let social: SocialRepository
    let onPublished: () -> Void

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var router: AppRouter
    @State private var title = ""
    @State private var type = "讲座"
    @State private var startsAt = Date().addingTimeInterval(24 * 3600)
    @State private var location = ""
    @State private var detail = ""
    @State private var officialUrl = ""
    @State private var trust: TrustProgress?
    @State private var working = false
    @State private var error: String?

    private let types = ["讲座", "宣讲", "演出", "赛事", "社团", "招新", "其他"]
    private var canPublish: Bool { (trust?.level ?? "T0") >= "T4" }
    private var formValid: Bool {
        title.trimmingCharacters(in: .whitespaces).count >= 2 && !working
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    OMHeader(eyebrow: "校园活动", title: "发布活动", lulu: .homeReply)
                    if let trust, !canPublish {
                        lockedCard(current: trust.level)
                    } else {
                        form
                    }
                }
                .padding(.horizontal, OMTheme.Spacing.pageX)
                .padding(.bottom, 44)
            }
            .background(OMPageBackground())
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("取消") { dismiss() } }
            }
        }
        .task { trust = try? await social.trust() }
        .accessibilityElement(children: .contain).accessibilityIdentifier("event-publish-sheet")
    }

    private var form: some View {
        VStack(alignment: .leading, spacing: 0) {
            OMCard {
                OMTextRole.t3("活动信息")
                TextField("活动标题（2–60 字）", text: $title)
                    .omInputStyle()
                    .padding(.top, OMTheme.Spacing.s3)
                OMSeg(items: types, label: { $0 }, selection: $type)
                    .padding(.top, OMTheme.Spacing.s3)
                DatePicker("开始时间", selection: $startsAt, displayedComponents: [.date, .hourAndMinute])
                    .font(OMTheme.TypeToken.callout)
                    .foregroundStyle(OMTheme.ColorToken.ink)
                    .padding(.top, OMTheme.Spacing.s3)
                TextField("地点（校区 / 场馆）", text: $location)
                    .omInputStyle()
                    .padding(.top, OMTheme.Spacing.s3)
                TextField("补充说明（选填）", text: $detail, axis: .vertical)
                    .omInputStyle(multiline: true)
                    .padding(.top, OMTheme.Spacing.s3)
                TextField("官方报名链接（选填）", text: $officialUrl)
                    .omInputStyle()
                    .keyboardType(.URL)
                    .textInputAutocapitalization(.never)
                    .padding(.top, OMTheme.Spacing.s3)
            }
            OMNote(text: "发布后全校同学可见；活动匿名展示，不显示你的身份。", sticker: "shield-check.png")
            if let error {
                OMCard { OMG5StateView(state: .networkError, message: error) }
            }
            OMButton(working ? "发布中…" : "发布活动", systemIcon: "paperplane", loading: working) {
                Task { await submit() }
            }
            .disabled(!formValid)
            .padding(.top, OMTheme.Spacing.s2)
            .accessibilityIdentifier("event-publish-submit")
        }
    }

    private func lockedCard(current: String) -> some View {
        OMCard {
            HStack(spacing: 10) {
                OMSticker("medal.png", size: .s44)
                VStack(alignment: .leading, spacing: 2) {
                    OMTextRole.t3("T4 校园主理人可发布")
                    OMTextRole.cap("发布校园活动需要信任等级达到 T4（当前 \(current)），经社团 / 院系 / 平台核验后开放。")
                }
                Spacer()
            }
            OMButton("查看信任进度", systemIcon: "medal", kind: .ghost, small: true, fillsWidth: false) {
                dismiss()
                router.push(.trust)
            }
            .padding(.top, OMTheme.Spacing.s3)
        }
        .accessibilityIdentifier("event-publish-locked")
    }

    private func submit() async {
        working = true
        defer { working = false }
        do {
            try await events.publish(CampusEventDraft(
                title: title.trimmingCharacters(in: .whitespaces),
                type: type,
                startsAt: startsAt,
                endsAt: nil,
                location: location.isEmpty ? nil : location,
                description: detail.isEmpty ? nil : detail,
                officialUrl: officialUrl.isEmpty ? nil : officialUrl
            ))
            onPublished()
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
