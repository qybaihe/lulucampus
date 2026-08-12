#if DEBUG
import Foundation

enum PrototypeScreenGroup: String, CaseIterable, Identifiable {
    case onboarding = "A · 启动与准入"
    case today = "B · 今天 / hermes"
    case publicGatherings = "C · 公开局"
    case intent = "D · 差一个 / 阿凑"
    case gatherings = "E · 我的局与搭子"
    case profile = "M · 我"
    case organizer = "O · 主理人台"
    case global = "G · 全局状态"
    case composite = "返回稿组合态"

    var id: String { rawValue }
}

/// 74 formal design nodes plus the two returned composite states B12.2 and MSG.
enum PrototypeScreenID: String, CaseIterable, Identifiable, Hashable {
    case a1 = "A1", a2 = "A2", a3 = "A3", a4 = "A4", a5 = "A5", a6 = "A6", a7 = "A7", a8 = "A8"
    case b1 = "B1", b2 = "B2", b3 = "B3", b31 = "B3.1", b4 = "B4", b41 = "B4.1"
    case b5 = "B5", b51 = "B5.1", b6 = "B6", b61 = "B6.1", b7 = "B7", b71 = "B7.1"
    case b8 = "B8", b9 = "B9", b10 = "B10", b11 = "B11", b12 = "B12", b121 = "B12.1"
    case c1 = "C1", c2 = "C2", c3 = "C3", c4 = "C4"
    case d1 = "D1", d2 = "D2", d3 = "D3", d31 = "D3.1", d32 = "D3.2", d33 = "D3.3", d34 = "D3.4", d4 = "D4"
    case e1 = "E1", e2 = "E2", e3 = "E3", e4 = "E4", e5 = "E5", e6 = "E6", e7 = "E7", e8 = "E8"
    case e9 = "E9", e10 = "E10", e11 = "E11", e12 = "E12", e13 = "E13", e14 = "E14", e15 = "E15", e16 = "E16", e17 = "E17"
    case m1 = "M1", m2 = "M2", m3 = "M3", m4 = "M4", m5 = "M5", m6 = "M6", m7 = "M7", m8 = "M8", m9 = "M9", m10 = "M10"
    case o1 = "O1", o2 = "O2", o3 = "O3", o4 = "O4"
    case g1 = "G1", g2 = "G2", g3 = "G3", g4 = "G4", g5 = "G5"
    case b122 = "B12.2"
    case msg = "MSG"

    var id: String { rawValue }

    var group: PrototypeScreenGroup {
        switch self {
        case .a1, .a2, .a3, .a4, .a5, .a6, .a7, .a8: .onboarding
        case .b1, .b2, .b3, .b31, .b4, .b41, .b5, .b51, .b6, .b61, .b7, .b71, .b8, .b9, .b10, .b11, .b12, .b121: .today
        case .c1, .c2, .c3, .c4: .publicGatherings
        case .d1, .d2, .d3, .d31, .d32, .d33, .d34, .d4: .intent
        case .e1, .e2, .e3, .e4, .e5, .e6, .e7, .e8, .e9, .e10, .e11, .e12, .e13, .e14, .e15, .e16, .e17: .gatherings
        case .m1, .m2, .m3, .m4, .m5, .m6, .m7, .m8, .m9, .m10: .profile
        case .o1, .o2, .o3, .o4: .organizer
        case .g1, .g2, .g3, .g4, .g5: .global
        case .b122, .msg: .composite
        }
    }

    var title: String {
        switch self {
        case .a1: "启动路由"
        case .a2: "价值引导"
        case .a3: "扫码认证"
        case .a4: "授权范围"
        case .a5: "画像初始化"
        case .a6: "画像确认"
        case .a7: "社交开关"
        case .a8: "系统权限"
        case .b1: "今天 / hermes"
        case .b2: "hermes 问答"
        case .b3: "我的课表"
        case .b31: "课程详情"
        case .b4: "作业与 DDL"
        case .b41: "作业详情"
        case .b5: "体育场馆"
        case .b51: "场馆时段选择"
        case .b6: "图书馆研讨室"
        case .b61: "研讨室时段选择"
        case .b7: "活动 / 宣讲会"
        case .b71: "活动详情"
        case .b8: "组会与课题"
        case .b9: "班车"
        case .b10: "场景触发浮层"
        case .b11: "个人行动预览"
        case .b12: "赛事库"
        case .b121: "赛事详情"
        case .c1: "公开局"
        case .c2: "公开局详情"
        case .c3: "准入门槛说明"
        case .c4: "缺口卡落地页"
        case .d1: "意图输入"
        case .d2: "澄清追问"
        case .d3: "意图卡确认"
        case .d31: "能力标签编辑"
        case .d32: "空档选择器"
        case .d33: "角色需求编辑"
        case .d34: "社交模式与安全偏好"
        case .d4: "招募中"
        case .e1: "我的局 / 搭子"
        case .e2: "局详情容器"
        case .e3: "多人确认"
        case .e4: "改约协商"
        case .e5: "预览与授权"
        case .e6: "执行结果"
        case .e7: "协作空间"
        case .e8: "补位面板"
        case .e9: "完成确认"
        case .e10: "复局选择"
        case .e11: "共同目标"
        case .e12: "退出 / 取消确认"
        case .e13: "举报与拉黑"
        case .e14: "局内群聊"
        case .e15: "搭子关系列表"
        case .e16: "搭子关系详情"
        case .e17: "解除关系"
        case .m1: "我"
        case .m2: "画像编辑"
        case .m3: "信任等级详情"
        case .m4: "授权管理"
        case .m5: "隐私与安全"
        case .m6: "匹配偏好"
        case .m7: "日历与通知"
        case .m8: "黑名单"
        case .m9: "申诉"
        case .m10: "账号与数据"
        case .o1: "管理台首页"
        case .o2: "创建官方局"
        case .o3: "报名与到场看板"
        case .o4: "局模板"
        case .g1: "hermes 唤起浮层"
        case .g2: "缺口卡分享 Sheet"
        case .g3: "重新扫码授权浮层"
        case .g4: "静默解散处理"
        case .g5: "空 / 错 / 加载态规范"
        case .b122: "牌桌 · 差一个"
        case .msg: "消息"
        }
    }

    var route: String {
        switch self {
        case .a1: "/"
        case .a2: "/onboarding"
        case .a3: "/auth/scan"
        case .a4: "/auth/grants"
        case .a5: "/auth/init"
        case .a6: "/auth/profile-confirm"
        case .a7: "/auth/social"
        case .a8: "/auth/permissions"
        case .b1: "/today"
        case .b2: "/today/ask"
        case .b3: "/today/timetable"
        case .b31: "/today/course/{id}"
        case .b4: "/today/assignments"
        case .b41: "/today/assignment/{id}"
        case .b5: "/today/gym"
        case .b51: "/today/gym/slots"
        case .b6: "/today/room"
        case .b61: "/today/room/slots"
        case .b7: "/today/events"
        case .b71: "/today/event/{id}"
        case .b8: "/today/research"
        case .b9: "/today/transit"
        case .b10: "/today#scene-trigger"
        case .b11: "/today/action/preview"
        case .b12: "/today/competitions"
        case .b121: "/today/competition/{id}"
        case .c1: "/open"
        case .c2: "/open/{id}"
        case .c3: "/open/{id}/requirement"
        case .c4: "/g/{share_token}"
        case .d1: "/intent"
        case .d2: "/intent/clarify"
        case .d3: "/intent/card"
        case .d31: "/intent/card/skills"
        case .d32: "/intent/card/availability"
        case .d33: "/intent/card/roles"
        case .d34: "/intent/card/safety"
        case .d4: "/intent/{id}/pooling"
        case .e1: "/gatherings"
        case .e2: "/gathering/{id}"
        case .e3: "/gathering/{id}/confirm"
        case .e4: "/gathering/{id}/reschedule"
        case .e5: "/gathering/{id}/action"
        case .e6: "/gathering/{id}/result"
        case .e7: "/gathering/{id}/space"
        case .e8: "/gathering/{id}/backfill"
        case .e9: "/gathering/{id}/complete"
        case .e10: "/gathering/{id}/recur"
        case .e11: "/goal/{id}"
        case .e12: "/gathering/{id}#cancel"
        case .e13: "/gathering/{id}/report"
        case .e14: "/gathering/{id}/chat"
        case .e15: "/companions"
        case .e16: "/companion/{relation_id}"
        case .e17: "/companion/{relation_id}#unlink"
        case .m1: "/me"
        case .m2: "/me/profile"
        case .m3: "/me/trust"
        case .m4: "/me/grants"
        case .m5: "/me/privacy"
        case .m6: "/me/preferences"
        case .m7: "/me/notifications"
        case .m8: "/me/blocks"
        case .m9: "/me/appeals"
        case .m10: "/me/account"
        case .o1: "/organizer"
        case .o2: "/organizer/gatherings/new"
        case .o3: "/organizer/gatherings/{id}/attendance"
        case .o4: "/organizer/templates"
        case .g1: "overlay://hermes"
        case .g2: "sheet://share-gap"
        case .g3: "sheet://reauthorize"
        case .g4: "state://silent-dissolve"
        case .g5: "state://library"
        case .b122: "/today/competition/{id}/table"
        case .msg: "/messages"
        }
    }

    var isReturnedReference: Bool { Self.returnedReferences.contains(self) }
    var isFormalNode: Bool { self != .b122 && self != .msg }

    static let returnedReferences: Set<Self> = [
        .a2, .a3, .a4, .a5, .a6, .a7,
        .b1, .b4, .b41, .b5, .b51, .b7, .b71, .b12, .b121,
        .c1, .c4,
        .d1, .d2, .d3, .d4,
        .e1, .e3, .e5, .e6, .e7, .e9, .e10, .e14, .e16, .e17,
        .m1, .m3, .g2,
        .b122, .msg
    ]

    static var formalNodes: [Self] { allCases.filter(\.isFormalNode) }
    static var missingReturnedReferences: [Self] { formalNodes.filter { !$0.isReturnedReference } }
}
#endif
