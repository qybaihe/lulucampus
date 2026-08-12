#if DEBUG
import SwiftUI

/// 原型屏分发：75 屏（74 正式节点 + MSG）+ B12.2 组合态。
/// 内容逐屏转写自 design/received/2026-08-12-one-more-lulu-frontend/export/js/screens-1..3.js。
struct PrototypeScreenView: View {
    let screen: PrototypeScreenID
    let actions: PrototypeActions

    var body: some View {
        switch screen {
        case .a1: A1Screen(actions: actions)
        case .a2: A2Screen(actions: actions)
        case .a3: A3Screen(actions: actions)
        case .a4: A4Screen(actions: actions)
        case .a5: A5Screen(actions: actions)
        case .a6: A6Screen(actions: actions)
        case .a7: A7Screen(actions: actions)
        case .a8: A8Screen(actions: actions)
        case .b1: B1Screen(actions: actions)
        case .b2: B2Screen(actions: actions)
        case .b3: B3Screen(actions: actions)
        case .b31: B31Screen(actions: actions)
        case .b4: B4Screen(actions: actions)
        case .b41: B41Screen(actions: actions)
        case .b5: B5Screen(actions: actions)
        case .b51: B51Screen(actions: actions)
        case .b6: B6Screen(actions: actions)
        case .b61: B61Screen(actions: actions)
        case .b7: B7Screen(actions: actions)
        case .b71: B71Screen(actions: actions)
        case .b8: B8Screen(actions: actions)
        case .b9: B9Screen(actions: actions)
        case .b10: B10Screen(actions: actions)
        case .b11: B11Screen(actions: actions)
        case .b12: B12Screen(actions: actions)
        case .b121: B121Screen(actions: actions)
        case .c1: C1Screen(actions: actions)
        case .c2: C2Screen(actions: actions)
        case .c3: C3Screen(actions: actions)
        case .c4: C4Screen(actions: actions)
        case .d1: D1Screen(actions: actions)
        case .d2: D2Screen(actions: actions)
        case .d3: D3Screen(actions: actions)
        case .d31: D31Screen(actions: actions)
        case .d32: D32Screen(actions: actions)
        case .d33: D33Screen(actions: actions)
        case .d34: D34Screen(actions: actions)
        case .d4: D4Screen(actions: actions)
        case .e1: E1Screen(actions: actions)
        case .e2: E2Screen(actions: actions)
        case .e3: E3Screen(actions: actions)
        case .e4: E4Screen(actions: actions)
        case .e5: E5Screen(actions: actions)
        case .e6: E6Screen(actions: actions)
        case .e7: E7Screen(actions: actions)
        case .e8: E8Screen(actions: actions)
        case .e9: E9Screen(actions: actions)
        case .e10: E10Screen(actions: actions)
        case .e11: E11Screen(actions: actions)
        case .e12: E12Screen(actions: actions)
        case .e13: E13Screen(actions: actions)
        case .e14: E14Screen(actions: actions)
        case .e15: E15Screen(actions: actions)
        case .e16: E16Screen(actions: actions)
        case .e17: E17Screen(actions: actions)
        case .m1: M1Screen(actions: actions)
        case .m2: M2Screen(actions: actions)
        case .m3: M3Screen(actions: actions)
        case .m4: M4Screen(actions: actions)
        case .m5: M5Screen(actions: actions)
        case .m6: M6Screen(actions: actions)
        case .m7: M7Screen(actions: actions)
        case .m8: M8Screen(actions: actions)
        case .m9: M9Screen(actions: actions)
        case .m10: M10Screen(actions: actions)
        case .o1: O1Screen(actions: actions)
        case .o2: O2Screen(actions: actions)
        case .o3: O3Screen(actions: actions)
        case .o4: O4Screen(actions: actions)
        case .g1: G1Screen(actions: actions)
        case .g2: G2Screen(actions: actions)
        case .g3: G3Screen(actions: actions)
        case .g4: G4Screen(actions: actions)
        case .g5: G5Screen(actions: actions)
        case .b122: B122Screen(actions: actions)
        case .msg: MSGScreen(actions: actions)
        }
    }
}

/// data-go 路由："__back" 出栈；"tab:x" 去主 Tab 根；其余按节点 ID 直达。
func prototypeGo(_ target: String, _ actions: PrototypeActions) {
    if target.isEmpty { return }
    if target == "__back" {
        actions.perform(.back)
        return
    }
    if target.hasPrefix("tab:") {
        switch String(target.dropFirst(4)) {
        case "today": actions.route(.b1)
        case "match": actions.route(.b12)
        case "create": actions.route(.d1)
        case "msg": actions.route(.msg)
        case "me": actions.route(.m1)
        default: break
        }
        return
    }
    if let id = PrototypeScreenID(rawValue: target) {
        actions.route(id)
    }
}

/// 卡片可点（data-go 在 .om-card 上）
extension View {
    func omCardTap(_ target: String, _ actions: PrototypeActions) -> some View {
        contentShape(Rectangle())
            .onTapGesture { prototypeGo(target, actions) }
            .accessibilityAddTraits(.isButton)
    }
}
#endif
