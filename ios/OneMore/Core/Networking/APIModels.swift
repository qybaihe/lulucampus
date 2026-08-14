import Foundation

enum CampusDayCodec {
    static let timeZone = TimeZone(identifier: "Asia/Shanghai")!

    static func string(from date: Date) -> String {
        let formatter = DateFormatter()
        formatter.calendar = Calendar(identifier: .gregorian)
        formatter.locale = Locale(identifier: "en_US_POSIX")
        formatter.timeZone = timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }
}

enum JSONValue: Codable, Hashable, Sendable {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() { self = .null }
        else if let value = try? container.decode(Bool.self) { self = .bool(value) }
        else if let value = try? container.decode(Double.self) { self = .number(value) }
        else if let value = try? container.decode(String.self) { self = .string(value) }
        else if let value = try? container.decode([String: JSONValue].self) { self = .object(value) }
        else { self = .array(try container.decode([JSONValue].self)) }
    }

    var stringValue: String? {
        if case let .string(value) = self { return value }
        return nil
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case let .string(value): try container.encode(value)
        case let .number(value): try container.encode(value)
        case let .bool(value): try container.encode(value)
        case let .object(value): try container.encode(value)
        case let .array(value): try container.encode(value)
        case .null: try container.encodeNil()
        }
    }
}

struct APIEnvelope<Value: Decodable & Sendable>: Decodable, Sendable {
    let data: Value
    let meta: [String: JSONValue]
}

struct APIErrorBody: Decodable, Hashable, Sendable {
    let code: String
    let message: String
    let details: [String: JSONValue]
    let requestId: String?
}

struct APIErrorEnvelope: Decodable, Sendable { let error: APIErrorBody }

enum APIClientError: LocalizedError, Equatable, Sendable {
    case invalidConfiguration
    case invalidResponse
    case transport(String)
    case server(status: Int, body: APIErrorBody)
    case decoding(String, requestID: String?)
    case sessionExpired(requestID: String?)
    case offline

    var errorDescription: String? {
        switch self {
        case .invalidConfiguration: "服务地址配置无效"
        case .invalidResponse: "服务响应无效"
        case let .transport(message): "网络连接失败：\(message)"
        case let .server(_, body): body.message
        case let .decoding(message, _): "数据格式不兼容：\(message)"
        case .sessionExpired: "登录已失效，请重新认证"
        case .offline: "当前离线，写操作将在联网后恢复"
        }
    }
}

extension Error {
    /// SwiftUI `.task` / 切 Tab 会取消进行中的请求；这不是网络故障。
    var isCancellation: Bool {
        if self is CancellationError { return true }
        if let url = self as? URLError, url.code == .cancelled { return true }
        let ns = self as NSError
        return ns.domain == NSURLErrorDomain && ns.code == NSURLErrorCancelled
    }
}

enum HTTPMethod: String, Sendable { case get = "GET", post = "POST", patch = "PATCH", delete = "DELETE" }

struct EmptyRequest: Encodable, Sendable {}

struct PushDeviceRegisterRequest: Encodable, Sendable {
    let token: String
    let platform = "ios"
}

struct PushDeviceDeactivateRequest: Encodable, Sendable { let token: String }
struct PushInstallationDeactivateRequest: Encodable, Sendable {
    let token: String
    let deactivationToken: String
}
struct PushDeviceRegistration: Decodable, Sendable {
    let id: String
    let active: Bool
    let deactivationToken: String
}
struct PushDeviceDeactivation: Decodable, Sendable {
    let active: Bool
    let deactivated: Int
}

enum GatheringStatus: String, Codable, CaseIterable, Sendable {
    case draft = "Draft", pooling = "Pooling", tentative = "Tentative"
    case confirmed = "Confirmed", previewed = "Previewed", executed = "Executed"
    case active = "Active", completed = "Completed", recurred = "Recurred"
    case archived = "Archived", dissolved = "Dissolved", unknown

    init(from decoder: Decoder) throws {
        let raw = try decoder.singleValueContainer().decode(String.self)
        self = GatheringStatus(rawValue: raw) ?? .unknown
    }

    var displayName: String {
        switch self {
        case .draft: "草稿"
        case .pooling: "招募中"
        case .tentative: "待确认"
        case .confirmed: "已确认"
        case .previewed: "待核对"
        case .executed: "已执行"
        case .active: "进行中"
        case .completed: "已完成"
        case .recurred: "已复局"
        case .archived: "已归档"
        case .dissolved: "已解散"
        case .unknown: "状态同步中"
        }
    }
}

struct TodaySummary: Codable, Sendable {
    struct TimelineItem: Codable, Identifiable, Sendable {
        var id: String {
            if let explicit = explicitId, !explicit.isEmpty { return explicit }
            return "\(kind)-\(courseId ?? gatheringId ?? title ?? "item")-\(startAt?.timeIntervalSince1970 ?? 0)"
        }
        let explicitId: String?
        let kind: String
        let title: String?
        let subtitle: String?
        let timeLabel: String?
        let courseId: String?
        let gatheringId: String?
        let courseCode: String?
        let courseName: String?
        let classCode: String?
        let startAt: Date?
        let endAt: Date?
        let location: String?
        let changed: Bool?
        let action: [String: JSONValue]?
        var displayTitle: String { title ?? courseName ?? "今日事项" }
        var displayTimeRange: String {
            if let timeLabel, !timeLabel.isEmpty { return timeLabel }
            guard let startAt else { return "" }
            let start = startAt.formatted(date: .omitted, time: .shortened)
            if let endAt {
                return "\(start)–\(endAt.formatted(date: .omitted, time: .shortened))"
            }
            return start
        }
        var displayDetail: String {
            [subtitle, location]
                .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty }
                .first ?? kindLabel
        }
        var kindLabel: String {
            switch kind {
            case "course": "课程"
            case "gathering": "活动"
            case "assignment": "作业"
            default: "日程"
            }
        }
        enum CodingKeys: String, CodingKey {
            case explicitId = "id"
            case kind, title, subtitle, timeLabel, courseId, gatheringId
            case courseCode, courseName, classCode, startAt, endAt, location, changed, action
        }
    }
    let generatedAt: Date
    let timeline: [TimelineItem]
    let pending: [[String: JSONValue]]
    let sceneTrigger: [String: JSONValue]?
}

/// 今天接口里的待处理项：确认局 / 行动预览。展示在消息 Tab，不堆在今天首页。
struct TodayAttentionItem: Identifiable, Equatable, Sendable {
    let id: String
    let title: String
    let badge: String?
    let deepLink: String

    static func list(from pending: [[String: JSONValue]]) -> [TodayAttentionItem] {
        var seen = Set<String>()
        var items: [TodayAttentionItem] = []
        for raw in pending {
            let gatheringID = raw["gathering_id"]?.stringValue
            let actionID = raw["action_id"]?.stringValue
            let link = raw["deep_link"]?.stringValue
            let key = gatheringID ?? actionID ?? link
            guard let key, let link, seen.insert(key).inserted else { continue }
            items.append(
                TodayAttentionItem(
                    id: key,
                    title: title(for: raw),
                    badge: raw["type"]?.stringValue == "confirmation" ? "差你 1 票" : nil,
                    deepLink: link
                )
            )
        }
        return items
    }

    private static func title(for raw: [String: JSONValue]) -> String {
        if raw["type"]?.stringValue == "confirmation" {
            if let name = raw["from_name"]?.stringValue?.trimmingCharacters(in: .whitespaces),
               !name.isEmpty {
                return "\(name) 有一个局等待你确认"
            }
            return "有一个局等待你确认"
        }
        if let title = raw["title"]?.stringValue?.trimmingCharacters(in: .whitespaces), !title.isEmpty {
            return "「\(title)」等待核对"
        }
        return "有一份行动预览等待核对"
    }
}

struct Timetable: Codable, Sendable {
    struct Entry: Codable, Identifiable, Sendable {
        var id: String { "\(courseId)-\(classCode)-\(startAt.timeIntervalSince1970)" }
        let courseId: String
        let courseCode: String
        let courseName: String
        let classCode: String
        let startAt: Date
        let endAt: Date
        let location: String?
        let changed: Bool
        let title: String?
        let timeLabel: String?
        let displayCode: String?
        let displayClassCode: String?
        var displayTitle: String { title ?? courseName }
        var displayTimeRange: String {
            if let timeLabel, !timeLabel.isEmpty { return timeLabel }
            return "\(startAt.formatted(date: .omitted, time: .shortened))–\(endAt.formatted(date: .omitted, time: .shortened))"
        }
        var friendlyMeta: String? {
            let parts = [displayCode, displayClassCode, location]
                .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
                .filter { !$0.isEmpty && !Self.isTechnicalCode($0) }
            return parts.isEmpty ? nil : parts.joined(separator: " · ")
        }
        static func isTechnicalCode(_ value: String) -> Bool {
            let text = value.trimmingCharacters(in: .whitespacesAndNewlines)
            if text.lowercased().hasPrefix("jwxt:") { return true }
            if text.allSatisfy(\.isNumber), text.count >= 12 { return true }
            if text.count >= 28, text.allSatisfy({ $0.isLetter || $0.isNumber || "-:_".contains($0) }) {
                return true
            }
            return false
        }
    }
    let week: Int
    let entries: [Entry]
    let updatedAt: Date?
    let source: String
}

struct CampusAssignment: Codable, Identifiable, Sendable {
    let id: String
    let courseId: String?
    let title: String
    let dueAt: Date
    let status: String
}

struct CampusAssignmentDetail: Codable, Identifiable, Sendable {
    struct Course: Codable, Sendable { let id: String; let code: String; let name: String }
    let id: String
    let title: String
    let dueAt: Date
    let status: String
    let course: Course?
    let sourceRef: String?
}

struct CampusCourseDetail: Codable, Identifiable, Sendable {
    let id: String
    let code: String
    let name: String
    let domain: String
    let capabilityTags: [String]
    let classCode: String
    let term: String
    let meetingWindows: [JSONValue]
    let privacy: String
}

struct HermesToolTrace: Codable, Sendable {
    let name: String
    let ok: Bool?
    let summary: String?
    let cardType: String?
}

struct HermesAskResult: Codable, Sendable {
    let kind: String
    let action: String?
    let cardType: String
    let data: JSONValue
    let requiresPreview: Bool
    let toolTrace: [HermesToolTrace]?
}

struct HermesPeer: Identifiable, Sendable, Equatable {
    let userId: String
    let displayName: String
    let personaLabel: String?
    let reason: String
    let overlap: String
    var id: String { userId }
}

struct HermesPeerChatResult: Codable, Sendable {
    let channelId: String
    let gatheringId: String
}

struct UserProfilePayload: Codable, Sendable {
    struct Capability: Codable, Identifiable, Sendable {
        var id: String { key }
        let key: String
        let label: String
        let source: String
        let weight: Double
        let hidden: Bool
    }
    struct CapabilityOption: Codable, Identifiable, Sendable {
        var id: String { key }
        let key: String
        let label: String
    }
    let userId: String
    let initStatus: String
    let initProgress: [String: JSONValue]
    let identity: [String: JSONValue]
    let capabilities: [Capability]
    let availableCapabilities: [CapabilityOption]
    let interestDomains: [String]
    let crossMajorScore: Double
    let trustProgress: [String: JSONValue]
    /// Compact Douyin taste card from GET /profile/me (null when not imported).
    let tasteProfile: TasteProfileSummary?
}

/// Compact taste card embedded in /profile/me (not the full TasteProfileResult).
struct TasteProfileSummary: Codable, Sendable {
    let status: String?
    let primaryTag: TasteTagScore?
    let secondaryTags: [String]?
    let interestDomains: [String]?
    let interestTags: [String]?
    let summary: String?
    let persona: String?
    let matchingHints: [String]?
    let confidence: Double?
    let calibrated: Bool?
    let source: String?
    let visibility: String?
}

struct CampusEvent: Codable, Identifiable, Sendable {
    let id: String
    let type: String
    let title: String
    let startsAt: Date?
    let endsAt: Date?
    let location: String?
    let officialUrl: URL?
    let details: [String: JSONValue]
    let registrationMode: String

    /// 列表 chip 用中文；兼容旧快照里的 teachin / seminar。
    var displayType: String {
        switch type {
        case "teachin", "宣讲会": "宣讲"
        case "seminar", "lecture": "讲座"
        case "club", "society": "社团"
        case "recruitment": "招新"
        case "career_fair", "招聘会": "招聘"
        case "performance": "演出"
        default: type
        }
    }
}

struct Competition: Codable, Identifiable, Sendable {
    struct TeamConstraints: Codable, Sendable { let teamSizeMin: Int; let teamSizeMax: Int; let eligibility: [String] }
    struct RequiredSkill: Codable, Sendable { let key: String; let label: String; let weight: Double }
    struct Stage: Codable, Sendable { let name: String; let startAt: Date?; let endAt: Date?; let mode: String?; let location: String?; let note: String? }
    let id: String
    let name: String
    let registrationDeadline: Date?
    let submissionDeadline: Date?
    let mode: String
    let location: String?
    let rewards: String?
    let registrationUrl: URL
    let sourceUrl: URL
    let priority: Int
    let stages: [Stage]
    let tracks: [String]
    let requiredSkills: [RequiredSkill]
    let participationMode: String
    let registrationMode: String
    let registrationInstructions: String?
    let feeNote: String?
    let recommendationTier: String
    let recommendationLabel: String
    let recommendationDescription: String
    let verifiedAt: Date?
    let teamFormingSupported: Bool
    let collaborationAction: String
    let teamConstraints: TeamConstraints
    var tasteFit: Double? = nil
    var tasteFitLabel: String? = nil
    var tasteFitReasons: [String] = []
    var recruitHints: [String] = []
    var recruitGapCount: Int = 0
    var recruitGapLabels: [String] = []
    var teamSizeMin: Int { teamConstraints.teamSizeMin }
    var teamSizeMax: Int { teamConstraints.teamSizeMax }

    /// 赛事卡贴纸：科研 → 烧瓶，创业/点子 → 灯泡，其余 → 奖杯。
    var sticker: String {
        let haystack = (name + " " + tracks.joined(separator: " ")).lowercased()
        if haystack.contains("科研") || haystack.contains("研究") || haystack.contains("论文")
            || haystack.contains("学术") || haystack.contains("实验") {
            return "flask.png"
        }
        if haystack.contains("创业") || haystack.contains("创新") || haystack.contains("商业")
            || haystack.contains("点子") || haystack.contains("创投") {
            return "bulb.png"
        }
        return "trophy.png"
    }

    /// 推荐档 label/description 以后端下发为准；旧快照缺字段时按稳定码兜底（文档允许 fallback）。
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decode(String.self, forKey: .name)
        registrationDeadline = try c.decodeIfPresent(Date.self, forKey: .registrationDeadline)
        submissionDeadline = try c.decodeIfPresent(Date.self, forKey: .submissionDeadline)
        mode = try c.decode(String.self, forKey: .mode)
        location = try c.decodeIfPresent(String.self, forKey: .location)
        rewards = try c.decodeIfPresent(String.self, forKey: .rewards)
        registrationUrl = try c.decode(URL.self, forKey: .registrationUrl)
        sourceUrl = try c.decode(URL.self, forKey: .sourceUrl)
        priority = try c.decode(Int.self, forKey: .priority)
        stages = try c.decode([Stage].self, forKey: .stages)
        tracks = try c.decode([String].self, forKey: .tracks)
        requiredSkills = try c.decode([RequiredSkill].self, forKey: .requiredSkills)
        participationMode = try c.decode(String.self, forKey: .participationMode)
        registrationMode = try c.decode(String.self, forKey: .registrationMode)
        registrationInstructions = try c.decodeIfPresent(String.self, forKey: .registrationInstructions)
        feeNote = try c.decodeIfPresent(String.self, forKey: .feeNote)
        recommendationTier = try c.decode(String.self, forKey: .recommendationTier)
        recommendationLabel = try c.decodeIfPresent(String.self, forKey: .recommendationLabel)
            ?? Self.fallbackLabels[recommendationTier] ?? "补充参考"
        recommendationDescription = try c.decodeIfPresent(String.self, forKey: .recommendationDescription)
            ?? Self.fallbackDescriptions[recommendationTier] ?? ""
        verifiedAt = try c.decodeIfPresent(Date.self, forKey: .verifiedAt)
        teamFormingSupported = try c.decode(Bool.self, forKey: .teamFormingSupported)
        collaborationAction = try c.decode(String.self, forKey: .collaborationAction)
        teamConstraints = try c.decode(TeamConstraints.self, forKey: .teamConstraints)
        tasteFit = try c.decodeIfPresent(Double.self, forKey: .tasteFit)
        tasteFitLabel = try c.decodeIfPresent(String.self, forKey: .tasteFitLabel)
        tasteFitReasons = try c.decodeIfPresent([String].self, forKey: .tasteFitReasons) ?? []
        recruitHints = try c.decodeIfPresent([String].self, forKey: .recruitHints) ?? []
        recruitGapCount = try c.decodeIfPresent(Int.self, forKey: .recruitGapCount) ?? 0
        recruitGapLabels = try c.decodeIfPresent([String].self, forKey: .recruitGapLabels) ?? []
    }

    private static let fallbackLabels = ["A": "优先推荐", "B": "可报名", "C": "补充参考"]
    private static let fallbackDescriptions = [
        "A": "",
        "B": "",
        "C": "",
    ]
}

/// GET /competitions/recommendation-tiers 目录项
struct RecommendationTierMeta: Codable, Identifiable, Sendable {
    var id: String { code }
    let code: String
    let label: String
    let description: String
    let sortOrder: Int
}

/// GET /competitions/{id}/teams 条目：招募中的赛事队伍（匿名结构，
/// 只有规模 / 池内人数 / 角色缺口，无成员身份）。
struct CompetitionTeam: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let gatheringType: String
    let status: GatheringStatus
    let location: String?
    let campus: String?
    let startAt: Date?
    let targetSize: Int
    let memberCount: Int
    let requiredRoles: [String]
    let expiresAt: Date?
    let goal: String?
    let missingCount: Int?
    let missingRoles: [String]?
    let filledRoles: [String]?
    var minSize: Int? = nil
    var rosterHighlights: [String]? = nil

    var filled: Int { min(memberCount, targetSize) }

    var sizeRangeLabel: String {
        if let minSize, minSize > 0, minSize != targetSize {
            return "\(minSize)–\(targetSize) 人"
        }
        return "\(targetSize) 人"
    }

    var resolvedMissingCount: Int {
        missingCount ?? max(0, targetSize - memberCount)
    }

    var resolvedMissingRoles: [String] {
        if let missingRoles, !missingRoles.isEmpty { return missingRoles }
        return requiredRoles
    }

    /// 角色缺口文案：「差一个算法」。
    var gapDescription: String? {
        let labels = resolvedMissingRoles.map(CapabilityLabel.displayName(for:))
        if labels.count == 1 { return "差一个\(labels[0])" }
        if labels.count > 1 {
            return "还差 \(labels.count) 个角色：\(labels.joined(separator: "、"))"
        }
        if resolvedMissingCount > 0 { return "还差 \(resolvedMissingCount) 人" }
        return nil
    }
}

/// 能力键 → 中文名。未知键原样透出（服务端可扩展）。
enum CapabilityLabel {
    private static let table: [String: String] = [
        "frontend": "前端", "backend": "后端", "design": "设计",
        "visual_design": "视觉", "product": "产品", "data_analysis": "数据分析",
        "machine_learning": "机器学习", "algorithm": "算法", "presentation": "路演",
        "writing": "文案", "paper_writing": "写作", "research": "调研", "video": "视频",
        "operations": "运营", "business_analysis": "商业分析",
        "modeling": "建模", "programming": "编程",
    ]
    static func displayName(for key: String) -> String { table[key] ?? key }
}

struct IntentCompileRequest: Codable, Sendable {
    let text: String
    var moodNote: String?
    var competitionId: String?
    var clarificationRound = 0
    var answers: [String: String] = [:]
}

struct IntentCard: Codable, Identifiable, Sendable {
    struct Capability: Codable, Sendable { let key: String; let source: String }
    struct Window: Codable, Sendable { let startAt: Date; let endAt: Date; let stability: Double }
    let id: String
    let status: String
    let gatheringType: String
    let mode: String
    let goal: String
    var moodNote: String? = nil
    let capabilities: [Capability]
    let requiredRoles: [String]
    let intensity: String
    let availableWindows: [Window]
    let campus: String?
    let minSize: Int
    let targetSize: Int
    let socialMode: String
    var sameGenderOnly: Bool? = nil
    let competitionId: String?
    let expiresAt: Date
    let fieldSources: [String: String]
    let clarificationRounds: Int
}

struct IntentCompileResult: Codable, Sendable {
    let card: IntentCard
    let needsClarification: Bool
    let questions: [IntentClarificationQuestion]
    let maxRounds: Int
    var tasteFitLabel: String? = nil
    var recruitHints: [String]? = nil
}

struct IntentClarificationQuestion: Codable, Hashable, Identifiable, Sendable {
    var id: String { key }
    let key: String
    let prompt: String
    let inputType: String
}

struct IntentCardPatch: Codable, Sendable {
    var gatheringType: String?
    var goal: String?
    var moodNote: String?
    var capabilities: [IntentCard.Capability]?
    var requiredRoles: [String]?
    var intensity: String?
    var availableWindows: [IntentCard.Window]?
    var campus: String?
    var minSize: Int?
    var targetSize: Int?
    var socialMode: String?
    var sameGenderOnly: Bool?
    var expiresAt: Date?
}

struct IntentPublishRequest: Codable, Sendable { let cardId: String }
struct IntentPublishResult: Codable, Sendable {
    let intentId: String
    let gatheringId: String
    let status: String
    let expiresAt: Date
}

struct RelationSummary: Codable, Identifiable, Sendable {
    struct Participant: Codable, Identifiable, Sendable {
        var id: String { userId }
        let userId: String
        let displayName: String?
        let college: String?
        let major: String?
        var interestTags: [String] = []
        var tasteSummary: String? = nil
    }
    struct Experience: Codable, Identifiable, Sendable {
        let id: String
        let participants: [String]
        let gatheringType: String
        let occurredAt: Date
        let outcome: String
        let commonGrounds: [String]
    }
    /// 搭子里程碑：1/3/5/10/20 次同局的纪念节点（纯事实，非互评）。
    struct Milestone: Codable, Sendable {
        let reached: Int
        let reachedLabel: String?
        let next: Int?
        let nextLabel: String?
        let remaining: Int?
    }
    /// 仅双方可见的经历时间线：把「后台日志」翻成「关系的物证」。
    struct TimelineEntry: Codable, Identifiable, Sendable {
        var id: String { gatheringId }
        let gatheringId: String
        let title: String?
        let gatheringType: String
        let occurredAt: Date
        let location: String?
        let durationMinutes: Int?
        let outcome: String
        let commonGrounds: [String]
        let viaRecurrence: Bool
    }
    struct NextWindow: Codable, Sendable {
        let startAt: Date
        let endAt: Date
    }
    struct GoalSummary: Codable, Sendable {
        let id: String
        let definition: String
        let currentValue: Double
        let targetValue: Double
        let unit: String
        let periodEnd: String
    }
    let id: String
    let participants: [Participant]
    let status: String
    let experiences: [Experience]
    let latestExperienceAt: Date?
    let channelId: String?
    var timesTogether: Int = 0
    var recurCount: Int = 0
    var isFixedPartner: Bool = false
    var partnerTitle: String? = nil
    var milestone: Milestone? = nil
    var timeline: [TimelineEntry] = []
    var nextWindow: NextWindow? = nil
    var activeGoal: GoalSummary? = nil
    var peerDisplayName: String? = nil
    var lastMessage: LastMessage? = nil

    struct LastMessage: Codable, Sendable {
        let content: String?
        var sentAt: Date? = nil
    }
}

struct ChannelHeader: Codable, Identifiable, Sendable {
    struct Peer: Codable, Identifiable, Sendable {
        var id: String { userId }
        let userId: String
        let displayName: String?
    }
    let id: String
    let kind: String
    let title: String
    var subtitle: String? = nil
    var gatheringId: String? = nil
    var relationId: String? = nil
    var peers: [Peer] = []
}

struct MessagePayload: Codable, Identifiable, Sendable {
    struct Location: Codable, Sendable {
        let latitude: Double
        let longitude: Double
        let label: String
        let address: String?
    }
    struct Image: Codable, Sendable {
        let mediaId: String
        let url: String
        let contentType: String
        let byteCount: Int
        let sha256: String
        let width: Int?
        let height: Int?
        let caption: String?
    }
    let id: String
    let channelId: String
    let senderId: String
    let senderType: String
    let contentType: String
    let content: String?
    let image: Image?
    let location: Location?
    let sentAt: Date
    var senderDisplayName: String? = nil
}

struct ChannelScenePolicy: Codable, Sendable {
    let mode: String
    let phase: String
    let sendingEnabled: Bool
    let liveConnectionEnabled: Bool
    let reason: String?
    let nextChangeAt: Date?
    let source: String
}

struct TrustProgress: Codable, Sendable {
    struct Unlock: Codable, Identifiable, Sendable {
        var id: String { capability }
        let capability: String
        let requiredLevel: String
        let unlocked: Bool
    }
    /// 解锁叙事进度：如「有效成局 2/3 次」，用于进度条渲染。
    struct MetricProgress: Codable, Identifiable, Sendable {
        var id: String { key }
        let key: String
        let label: String
        let current: Double
        let required: Double
        let unit: String
    }
    /// 升到下一级的结构化条件（含进度与是否已满足）。
    struct Condition: Codable, Identifiable, Sendable {
        var id: String { key }
        let key: String
        let label: String
        let met: Bool
        var current: Double? = nil
        var required: Double? = nil
        var unit: String? = nil
        var detail: String? = nil

        var hasMetric: Bool {
            guard let required, required > 0, unit != nil, !(unit?.isEmpty ?? true) else { return false }
            // Binary flags use 0/1 with nil unit or unit-less; skip bars for pure checklists.
            return unit != nil && current != nil
        }

        var ratio: Double {
            guard let current, let required, required > 0 else { return met ? 1 : 0 }
            if key == "late_exit_rate" || label.contains("越低越好") {
                return met ? 1 : max(0, 1 - min(1, current / required))
            }
            return met ? 1 : min(1, current / required)
        }

        var metricText: String {
            guard let current, let required, let unit, !unit.isEmpty else {
                return met ? "已完成" : (detail ?? "未完成")
            }
            if unit == "%" {
                let cur = current == floor(current) ? String(Int(current)) : String(format: "%.1f", current)
                let req = required == floor(required) ? String(Int(required)) : String(format: "%.1f", required)
                if key == "late_exit_rate" || label.contains("越低越好") {
                    return "\(cur)% / 低于 \(req)%"
                }
                return "\(cur)% / \(req)%"
            }
            let cur = current == floor(current) ? String(Int(current)) : String(format: "%.1f", current)
            let req = required == floor(required) ? String(Int(required)) : String(format: "%.1f", required)
            return "\(cur) / \(req) \(unit)"
        }
    }
    /// 升级文档条目：每一级的达标标准与权益。
    struct LevelGuideItem: Codable, Identifiable, Sendable {
        var id: String { level }
        let level: String
        let name: String
        let how: String
        var benefits: [String] = []
        var isCurrent: Bool = false
        var isReached: Bool = false
    }
    let level: String
    let levelName: String
    var levelNarrative: String? = nil
    let nextLevel: String?
    var nextLevelName: String? = nil
    var nextLevelProgress: [MetricProgress] = []
    var conditions: [Condition] = []
    var currentBenefits: [String] = []
    var nextBenefits: [String] = []
    var overallProgress: Double = 0
    var levelGuide: [LevelGuideItem] = []
    let gaps: [String]
    let statistics: [String: JSONValue]
    let unlocks: [Unlock]?
    let observation: [String: JSONValue]?
}

struct NotificationPreferences: Codable, Sendable {
    struct Categories: Codable, Sendable {
        var gatheringUpdates: Bool
        var actionUpdates: Bool
        var chatMessages: Bool
        var trustUpdates: Bool
        var competitionDeadlines: Bool
        var scheduleReminders: Bool

        init(
            gatheringUpdates: Bool = true,
            actionUpdates: Bool = true,
            chatMessages: Bool = true,
            trustUpdates: Bool = true,
            competitionDeadlines: Bool = true,
            scheduleReminders: Bool = true
        ) {
            self.gatheringUpdates = gatheringUpdates
            self.actionUpdates = actionUpdates
            self.chatMessages = chatMessages
            self.trustUpdates = trustUpdates
            self.competitionDeadlines = competitionDeadlines
            self.scheduleReminders = scheduleReminders
        }

        init(from decoder: Decoder) throws {
            let container = try decoder.container(keyedBy: CodingKeys.self)
            gatheringUpdates = try container.decodeIfPresent(Bool.self, forKey: .gatheringUpdates) ?? true
            actionUpdates = try container.decodeIfPresent(Bool.self, forKey: .actionUpdates) ?? true
            chatMessages = try container.decodeIfPresent(Bool.self, forKey: .chatMessages) ?? true
            trustUpdates = try container.decodeIfPresent(Bool.self, forKey: .trustUpdates) ?? true
            competitionDeadlines = try container.decodeIfPresent(Bool.self, forKey: .competitionDeadlines) ?? true
            scheduleReminders = try container.decodeIfPresent(Bool.self, forKey: .scheduleReminders) ?? true
        }
    }
    var overallEnabled: Bool
    var calendarSyncEnabled: Bool
    var categories: Categories
    let systemSettingsManagedLocally: [String]
}

struct InboxNotification: Codable, Identifiable, Sendable {
    let id: String
    let type: String
    let category: String?
    let title: String?
    let payload: [String: JSONValue]
    let createdAt: Date
    let deliveredAt: Date?

    var summary: String {
        payload["summary"]?.stringValue ?? title ?? "你有一条新提醒"
    }

    var resolvedCategory: String {
        if let category, !category.isEmpty { return category }
        switch type {
        case "schedule_reminder", "assignment_reminder": return "schedule_reminders"
        case "chat_message": return "chat_messages"
        case "trust_level_changed": return "trust_updates"
        case "competition_deadline": return "competition_deadlines"
        case "execution_succeeded", "authorization_required", "reauthorization_required",
             "action_modification_requested", "calendar_revoked":
            return "action_updates"
        default: return "gathering_updates"
        }
    }

    var categoryLabel: String {
        switch resolvedCategory {
        case "schedule_reminders": "日程"
        case "gathering_updates": "成局"
        case "chat_messages": "消息"
        case "action_updates": "行动"
        case "trust_updates": "信任"
        case "competition_deadlines": "赛事"
        default: "提醒"
        }
    }

    var routingUserInfo: [AnyHashable: Any] {
        var values: [AnyHashable: Any] = ["type": type]
        for (key, value) in payload {
            if let string = value.stringValue {
                values[key] = string
            } else if case let .bool(flag) = value {
                values[key] = flag
            }
        }
        return values
    }
}

struct SocialPreferences: Codable, Sendable {
    var socialEnabled: Bool
    var courseMatchingEnabled: Bool
    var identityDisclosure: String
    var sameGenderOnly: Bool
    var minimumGroupSize: Int
    let sceneSensitivePolicy: String
}

struct MatchingPreferences: Codable, Sendable {
    var interactionStyle: String
    var sportLevel: String
    var studyIntensity: String
}

struct BlockedUser: Codable, Identifiable, Sendable {
    var id: String { blockedUserId }
    let blockedUserId: String
    let createdAt: Date
}

struct GatheringSummary: Codable, Identifiable, Sendable {
    struct Participant: Codable, Identifiable, Sendable {
        var id: String { userId }
        let userId: String
        let displayName: String?
        let college: String?
        let major: String?
        let role: String?
        var interestTags: [String] = []
        var tasteSummary: String? = nil
    }
    struct RecurrenceDecision: Codable, Sendable {
        let decision: String
        let keptUserIds: [String]
        let cloneGatheringId: String?
    }
    struct LeaveCapability: Codable, Sendable {
        let enabled: Bool
        let trustImpact: String
        let message: String
        let lateExitCutoff: Date?
        let serverNow: Date
        let disabledReason: String?
    }
    let id: String
    let title: String
    let goal: String
    var moodNote: String? = nil
    let gatheringType: String
    let mode: String
    let status: GatheringStatus
    let campus: String?
    let sameGenderOnly: Bool
    var identityDisclosure: String? = nil
    let startAt: Date?
    let endAt: Date?
    let location: String?
    var minSize: Int? = nil
    let targetSize: Int
    let requiredTrustLevel: String
    let requiredRoles: [String]
    let matchReason: String?
    var lookingFor: [String]? = nil
    let myConfirmation: String?
    let confirmedCount: Int?
    let memberCount: Int?
    let participants: [Participant]?
    var reportableParticipants: [Participant] = []
    let myRecurrenceDecision: RecurrenceDecision?
    let leaveCapability: LeaveCapability?
    let channelId: String?
    let actionId: String?
    let expiresAt: Date?
}

/// The leave endpoint intentionally returns only the authoritative terminal
/// state because the departing member is no longer entitled to a full view.
struct GatheringLeaveResult: Codable, Sendable {
    let id: String
    let status: GatheringStatus
}

struct DepartedSafetyContext: Codable, Identifiable, Sendable {
    var id: String { gatheringId }
    let gatheringId: String
    let title: String
    let gatheringType: String
    let status: GatheringStatus
    let leftAt: Date
    let reportableParticipants: [GatheringSummary.Participant]
}

struct GapShare: Codable, Sendable {
    let shareToken: String
    let gatheringId: String
    let gatheringType: String
    let title: String
    let goal: String
    var moodNote: String? = nil
    let status: GatheringStatus
    let campus: String?
    var startAt: Date? = nil
    var endAt: Date? = nil
    var targetSize: Int? = nil
    var missingCount: Int? = nil
    let expiresAt: Date?
    let joinable: Bool
    let deepLink: URL
    let universalLink: URL
    var lookingFor: [String]? = nil
}

/// 成局后 30 秒破冰包：为什么是你们 / 第一句怎么开 / 下一步是什么。
struct IcebreakerPack: Codable, Sendable {
    struct Fact: Codable, Identifiable, Sendable {
        var id: String { kind + text }
        let kind: String
        let text: String
    }
    struct NextSteps: Codable, Sendable {
        let startAt: Date?
        let endAt: Date?
        let location: String?
        let campus: String?
        let channelId: String?
        let checklist: [String]
    }
    let gatheringId: String
    let headline: String
    let facts: [Fact]
    let firstLines: [String]
    let nextSteps: NextSteps
}

/// 学期成局回忆录：服务端事实聚合，分享文案不含他人身份。
struct SemesterRecap: Codable, Sendable {
    struct TopPartner: Codable, Sendable {
        let displayName: String?
        let timesTogether: Int
    }
    struct TypeCount: Codable, Identifiable, Sendable {
        var id: String { gatheringType }
        let gatheringType: String
        let count: Int
    }
    let termLabel: String
    let since: Date
    let gatheringsCompleted: Int
    let partnersMet: Int
    let totalHours: Double
    let recurrences: Int
    let topPartner: TopPartner?
    let topTypes: [TypeCount]
    let topLocation: String?
    let highlights: [String]
    let shareText: String
}

struct GatheringActionCapability: Codable, Sendable {
    struct PendingModification: Codable, Sendable {
        let actionId: String
        let reason: String
        let proposedParams: [String: JSONValue]
        let createdAt: Date
    }
    let enabled: Bool
    let action: String?
    let params: [String: JSONValue]
    let disabledReason: String?
    let pendingModification: PendingModification?
}

struct GatheringBookingOption: Codable, Identifiable, Sendable {
    var id: String { optionToken }
    let optionToken: String
    let resourceType: String
    let action: String
    let location: String
    let startAt: Date
    let endAt: Date
    let label: String
}

struct BackfillOpportunity: Codable, Sendable {
    struct FallbackOption: Codable, Identifiable, Sendable {
        var id: String { key }
        let key: String
        let title: String
        let summary: String
        let minSize: Int
        let targetSize: Int
        let location: String?
    }
    let gatheringId: String
    let open: Bool
    let fastLaneActive: Bool
    let fastLaneUntil: Date?
    let viewerFastLaneEligible: Bool
    let viewerHasMatchingIntent: Bool
    let claimAvailableAt: Date?
    let historyVisible: Bool
    let viewerIsMember: Bool
    let fallbackOptions: [FallbackOption]
}

struct InitiateGatheringDraft: Codable, Sendable {
    var title: String
    var goal: String
    var gatheringType: String
    var mode = "similar"
    var campus: String?
    var location: String?
    var startAt: Date?
    var endAt: Date?
    var minSize = 3
    var targetSize = 4
    var requiredRoles: [String] = []
    var crossCollege = false
}

struct SharedGoal: Codable, Identifiable, Sendable {
    struct Milestone: Codable, Identifiable, Sendable {
        var id: String { "\(fraction)-\(targetValue)" }
        let fraction: Double
        let targetValue: Double
        let reached: Bool
        let reachedAt: Date?
    }

    struct MemberProgress: Codable, Identifiable, Sendable {
        var id: String { userId }
        let userId: String
        let displayName: String?
        let currentValue: Double
        let lastProgressAt: Date?
    }

    let id: String
    let relationId: String
    let definition: String
    let periodStart: String
    let periodEnd: String
    let targetValue: Double
    let currentValue: Double
    let unit: String
    let status: String
    let milestones: [Milestone]
    let memberProgress: [MemberProgress]
    let nextAction: String?
    let lastBroadcast: String?
    let lastProgressAt: Date?
    let progressSource: String
}

struct AuthorizationGrantView: Codable, Identifiable, Sendable {
    var id: String { scope }
    let scope: String
    let granted: Bool
    let grantedAt: Date?
    let revokedAt: Date?
}

struct IdentityFacts: Codable, Sendable {
    struct SessionHealth: Codable, Identifiable, Sendable {
        var id: String { subsystem }
        let subsystem: String
        let healthy: Bool
        let lastCheckedAt: Date?
        let errorCategory: String?
    }
    let userId: String
    let displayName: String?
    let verified: Bool
    let college: String?
    let major: String?
    let gradeYear: Int?
    let campus: String?
    let genderCode: String?
    let socialEnabled: Bool
    let grants: [AuthorizationGrantView]
    let sessionHealth: [SessionHealth]
}

struct TextMessageCreate: Codable, Sendable {
    let content: String
    let contentType: String

    init(content: String) {
        self.content = content
        contentType = "text"
    }
}

struct ImageMessageCreate: Codable, Sendable {
    struct Reference: Codable, Sendable { let mediaId: String; let caption: String? }
    let contentType: String
    let image: Reference

    init(image: Reference) {
        contentType = "image"
        self.image = image
    }
}

struct LocationMessageCreate: Codable, Sendable {
    struct Payload: Codable, Sendable { let latitude, longitude: Double; let label: String; let address: String? }
    let contentType: String
    let location: Payload

    init(location: Payload) {
        contentType = "location"
        self.location = location
    }
}

struct ImageAsset: Codable, Sendable {
    let mediaId, url, contentType, sha256: String
    let byteCount: Int
    let width, height: Int?
}

struct TasteImportCreate: Codable, Sendable { var force = false; var maxItems: Int? = nil }

struct TasteFromLinkRequest: Codable, Sendable {
    var shareUrl: String
    var likesLimit: Int = 30
    var postsLimit: Int = 20
    var collectsLimit: Int = 30
    var useLlm: Bool = true
    var force: Bool = true
}

struct TasteProgressPayload: Codable, Sendable {
    let phase: String
    let current: Int
    let total: Int?
    let percent: Double?
    let message: String
    let qrScanned: Bool?
    let phoneMasked: String?
    let codeSent: Bool?
}

struct TasteCollectionPayload: Codable, Sendable {
    let itemsCollected: Int
    let apiPages: Int
    let hasMore: Bool
}

struct TasteSourceProfile: Codable, Sendable {
    let uid: String?
    let secUid: String?
    let nickname: String?
    let avatarUrl: String?
}

struct TasteTagScore: Codable, Identifiable, Sendable {
    var id: String { key }
    let key: String
    let label: String
    let score: Double
}

struct TasteDomainScore: Codable, Identifiable, Sendable {
    var id: String { key }
    let key: String
    let label: String
    let score: Double
}

struct TasteInterestFacet: Codable, Identifiable, Sendable {
    var id: String { "\(domain)-\(facet)-\(label)" }
    let domain: String
    let facet: String
    let label: String
    let source: String?
    let questionId: String?
}

struct TasteSampleSummary: Codable, Sendable {
    let items: Int?
    let uniqueAuthors: Int?
    let apiPages: Int?
    let calibrated: Bool?
    let calibratedAt: String?
    let interestFacets: [TasteInterestFacet]?
    let generation: String?
    let llmProvider: String?
    let llmModel: String?
    let persona: String?
    let matchingHints: [String]?
    let tone: String?
    let llmError: String?
}

/// Unified taste result used by /taste/me, ai-refresh, answers, and import.result.
struct TasteProfileResult: Codable, Sendable {
    let status: String
    let primaryTag: TasteTagScore
    let secondaryTags: [TasteTagScore]
    let interestDomains: [TasteDomainScore]
    let interestFacets: [TasteInterestFacet]
    let dimensions: [String: Double]
    let summary: String
    let persona: String?
    let matchingHints: [String]
    let confidence: Double
    let calibrated: Bool
    let calibratedAt: String?
    let sample: TasteSampleSummary?
    let source: String
    let modelVersion: String
    let visibility: String

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        status = try container.decodeIfPresent(String.self, forKey: .status) ?? "READY"
        primaryTag = try container.decode(TasteTagScore.self, forKey: .primaryTag)
        secondaryTags = try container.decodeIfPresent([TasteTagScore].self, forKey: .secondaryTags) ?? []
        interestDomains = try container.decodeIfPresent([TasteDomainScore].self, forKey: .interestDomains) ?? []
        interestFacets = try container.decodeIfPresent([TasteInterestFacet].self, forKey: .interestFacets) ?? []
        dimensions = try container.decodeIfPresent([String: Double].self, forKey: .dimensions) ?? [:]
        summary = try container.decodeIfPresent(String.self, forKey: .summary) ?? ""
        persona = try container.decodeIfPresent(String.self, forKey: .persona)
        matchingHints = try container.decodeIfPresent([String].self, forKey: .matchingHints) ?? []
        confidence = try container.decodeIfPresent(Double.self, forKey: .confidence) ?? 0
        calibrated = try container.decodeIfPresent(Bool.self, forKey: .calibrated) ?? false
        calibratedAt = try container.decodeIfPresent(String.self, forKey: .calibratedAt)
        sample = try container.decodeIfPresent(TasteSampleSummary.self, forKey: .sample)
        source = try container.decodeIfPresent(String.self, forKey: .source) ?? "douyin"
        modelVersion = try container.decodeIfPresent(String.self, forKey: .modelVersion) ?? "taste-v2"
        visibility = try container.decodeIfPresent(String.self, forKey: .visibility) ?? "private"
    }
}

struct TasteImportStatus: Codable, Identifiable, Sendable {
    let id: String
    let source: String
    let status: String
    let expiresAt: Date
    let qrExpiresAt: Date?
    let qrImageDataUrl: String?
    let qrVersion: Int
    let progress: TasteProgressPayload
    let collection: TasteCollectionPayload?
    let sourceProfile: TasteSourceProfile?
    let candidateTags: [TasteTagScore]
    let questionCount: Int
    /// Embedded quiz package when READY and not yet calibrated (taste-quiz-v1).
    var questions: TasteQuestionSet? = nil
    let result: TasteProfileResult?
    let error: [String: String]?
}

struct TasteQRLoginView: Codable, Sendable {
    let importId: String
    let status: String
    let qrImageDataUrl: String?
    let qrVersion: Int
    let qrExpiresAt: Date?
    let qrImageUrl: String
    let phoneCode: String
    let verify: String
    let error: [String: String]?
}

struct TastePhoneLoginStatus: Codable, Sendable {
    let importId: String
    let status: String
    let phoneMasked: String?
    let codeSent: Bool
    let verified: Bool
    let authenticatedAt: Date?
    let submitCode: String
    let verify: String
    let error: [String: String]?
}

struct TasteLoginVerification: Codable, Sendable {
    let importId: String
    let status: String
    let verified: Bool
    let authenticatedAt: Date?
    let sourceProfile: TasteSourceProfile?
    let next: String
    let error: [String: String]?
}

/// Quiz JSON package from GET /profile/imports/{id}/questions (or embedded in status).
struct TasteQuestionSet: Codable, Sendable {
    struct Question: Codable, Identifiable, Sendable {
        struct Option: Codable, Identifiable, Sendable { let id: String; let label: String }
        let id: String
        let prompt: String
        let options: [Option]
        let required: Bool
        let type: String
    }
    var schemaVersion: String? = "taste-quiz-v1"
    let importId: String
    let candidateTags: [TasteTagScore]
    let questions: [Question]
    var calibrated: Bool? = nil
    var optional: Bool? = nil
    var minAnswers: Int? = 3
    var maxAnswers: Int? = 5
    var intro: String? = nil
    var submitPath: String? = nil

    var minimumSelections: Int { max(1, minAnswers ?? 3) }
}

struct TasteQuizAnswer: Codable, Sendable {
    let questionId: String
    let optionId: String
}

struct GatheringTimeOption: Codable, Identifiable, Sendable {
    var id: String { "\(startAt.timeIntervalSince1970)-\(endAt.timeIntervalSince1970)" }
    let startAt: Date
    let endAt: Date
    let feasibleCount: Int
    let stability: Double
    let campusReachable: Bool
}

struct RescheduleProposal: Codable, Identifiable, Sendable {
    var id: String { proposalId }
    let proposalId: String
    let gatheringId: String
    let status: String
    let startAt: Date
    let endAt: Date
    let feasibleCount: Int
    let acceptedCount: Int
    let requiredCount: Int
    let myVote: String?
    let expiresAt: Date?
    let decidedAt: Date?
}

struct CampusAction: Codable, Identifiable, Sendable {
    struct Authorization: Codable, Sendable {
        let requiredCount: Int
        let authorizedCount: Int
        let actorDecision: String
        let allAuthorized: Bool
    }
    struct Modification: Codable, Sendable {
        let reason: String
        let proposedParams: [String: JSONValue]
        let status: String
        let createdAt: Date
    }
    let id: String
    let userId: String
    let gatheringId: String?
    let actionName: String
    let status: String
    let params: [String: JSONValue]
    let previewSnapshot: [String: JSONValue]
    let snapshotHash: String
    let authorization: Authorization
    let modification: Modification?
    let executionResult: [String: JSONValue]?
    let errorCategory: String?

    /// 找球友时段模板：没有授权行，也不能提交预约。
    var isReferencePreview: Bool {
        if previewSnapshot["source"]?.stringValue == "peer_overlap_template" {
            return true
        }
        return gatheringId == nil && authorization.actorDecision == "not_required"
    }
}

struct MentionAzouResult: Codable, Sendable {
    let message: MessagePayload
    let actionHint: [String: JSONValue]?
}

struct TrustAppeal: Codable, Identifiable, Sendable {
    let id: String
    let reason: String
    let status: String
    let result: String?
    let createdAt: Date
    let updatedAt: Date
    let decidedAt: Date?
}

struct OfficialTemplate: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let goal: String
    let gatheringType: String
    let campus: String?
    let location: String
    let durationMinutes: Int
    let minSize: Int
    let targetSize: Int
    let requiredRoles: [String]
    let recurrenceRule: String?
    let active: Bool
    let createdAt: Date
    let updatedAt: Date
}

struct OfficialTemplateDraft: Codable, Sendable {
    var title: String
    var goal: String
    var gatheringType: String
    var campus: String?
    var location: String
    var durationMinutes: Int
    var minSize: Int
    var targetSize: Int
    var requiredRoles: [String]
    var recurrenceRule: String?
}

struct OrganizerQuotaBatch: Codable, Identifiable, Hashable, Sendable {
    var id: String { "\(label)-\(slots)" }
    var label: String
    var slots: Int
}

struct OfficialGatheringSummary: Codable, Identifiable, Sendable {
    let id: String
    let title: String
    let status: String
    let startAt: Date?
    let targetSize: Int
}

struct OfficialGatheringCreateResult: Codable, Identifiable, Sendable {
    let id: String
    let status: String
    let isOfficial: Bool
}

struct OfficialGatheringDraft: Codable, Sendable {
    var title: String
    var goal: String
    var gatheringType: String
    var startAt: Date
    var endAt: Date
    var location: String
    var campus: String?
    var minSize: Int
    var targetSize: Int
    var requiredRoles: [String]
    var quotaBatches: [OrganizerQuotaBatch]
}

struct OrganizerDashboard: Codable, Sendable {
    struct Participant: Codable, Identifiable, Sendable {
        var id: String { userId }
        let userId: String
        let displayName: String?
        let confirmationStatus: String
        let attended: Bool
    }

    let gatheringId: String
    let status: String
    let targetSize: Int
    let registeredCount: Int
    let confirmedCount: Int
    let attendedCount: Int
    let quotaBatches: [OrganizerQuotaBatch]
    let participants: [Participant]?
    let identityVisibility: String
}

struct OrganizerGatheringStatus: Codable, Identifiable, Sendable {
    let id: String
    let status: String
}

struct OrganizerAttendanceResult: Codable, Sendable {
    let userId: String
    let attended: Bool
}

struct LoginSessionCreate: Codable, Sendable {
    let deviceInstallId: String?
    let resumeUserId: String?
}

struct LoginSession: Codable, Identifiable, Sendable {
    let id: String
    let userId: String
    let status: String
    let qrImageDataUrl: String?
    let deepLink: String?
    let expiresAt: Date
    let accessToken: String?
    let redemptionToken: String?
    let errorCategory: String?
}

struct LoginRedemptionRequest: Codable, Sendable { let redemptionToken: String }
struct LoginRedemptionResult: Codable, Sendable { let accessToken: String }

struct PhoneRegisterBody: Codable, Sendable {
    let phone: String
    let password: String
    let displayName: String?
}

struct PhoneLoginBody: Codable, Sendable {
    let phone: String
    let password: String
}

struct PhoneAuthResult: Codable, Sendable {
    let accessToken: String
    let userId: String
    let displayName: String?
    let isNewUser: Bool
}
