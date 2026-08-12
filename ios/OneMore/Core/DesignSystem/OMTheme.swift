import SwiftUI

/// 用户可见的品牌架构。工程 target、bundle id 与 deep link 继续沿用 OneMore，
/// 「差一个」继续作为中央成局动作，不与 App 总品牌混用。
enum AppBrand {
    static let displayName = "噜噜成局"
    static let mascotName = "噜噜"
    static let coreAction = "差一个"
    static let slogan = "差一个，就成局"
    static let descriptor = "校园成局助手"
    static let loadingMessage = "噜噜正在取数，稍等一下。"
}

/// ONE MORE visual tokens transcribed from the frozen 2026-08-12 Lulu light
/// return (`design/received/2026-08-12-one-more-lulu-frontend/export/css/tokens.css`).
///
/// Seven base colors only; derived colors are oklch mixes of the base seven.
/// Semantic hard rules: `gap == yolk` (highest visual weight on screen),
/// `ready == ink`. A gap is never expressed with red.
enum OMTheme {
    enum ColorToken {
        // — 基础色板（七色，不新增） —
        static let paper = Color(hex: 0xF6F4EC)
        static let ink = Color(hex: 0x1F2D25)
        static let yolk = Color(hex: 0xF6C945)
        static let card = Color(hex: 0xFFFDF8)
        static let mist = Color(hex: 0x5D6B63)
        static let line = Color(hex: 0xDCE3D9)
        static let sage = Color(hex: 0xCBD4CC)

        // — 派生色（仅由基础色在 oklch 混合，与 tokens.css 一致） —
        static let ink60 = Color(hex: 0x6A776F)
        static let ink12 = Color(hex: 0xDCE3DF)
        static let ink06 = Color(hex: 0xEBF1ED)
        static let yolk30 = Color(hex: 0xFCEEC9)
        static let yolk14 = Color(hex: 0xFEF6E2)
        static let mist40 = Color(hex: 0xB1BCB6)
        /// color-mix(ink 16%, yolk)：主按钮与缺口徽章的描边
        static let yolkBorder = Color(hex: 0xD3AD40)
        /// color-mix(ink 18%, yolk)：中央「差一个」按钮描边
        static let yolkBorderStrong = Color(hex: 0xCEA940)

        // — 语义别名（硬规则） —
        /// 缺口 / 还差一个：全屏最高视觉权重
        static let gap = yolk
        static let gapSoft = yolk14
        /// 已就位 / 已具备
        static let ready = ink
        static let readySoft = ink06
    }

    enum Radius {
        static let small: CGFloat = 8
        static let medium: CGFloat = 14
        static let large: CGFloat = 20
        static let xLarge: CGFloat = 28
        static let pill: CGFloat = 999
        static let borderWidth: CGFloat = 1
    }

    /// 4pt 基线栅格
    enum Spacing {
        static let s1: CGFloat = 4
        static let s2: CGFloat = 8
        static let s3: CGFloat = 12
        static let s4: CGFloat = 16
        static let s5: CGFloat = 20
        static let s6: CGFloat = 24
        static let s8: CGFloat = 32
        static let s10: CGFloat = 40
        static let pageX: CGFloat = 20
    }

    /// 字号阶梯以 17px 正文为基准，经 SwiftUI TextStyle 获得 Dynamic Type。
    enum TypeToken {
        static let hero = Font.system(.largeTitle, design: .default, weight: .bold)       // 34
        static let title1 = Font.system(.title, design: .default, weight: .bold)          // 28
        static let title2 = Font.system(.title2, design: .default, weight: .bold)         // 22
        static let title3 = Font.system(.headline, design: .default, weight: .bold)       // 17
        static let body = Font.system(.body, design: .default, weight: .regular)          // 17
        static let callout = Font.system(.subheadline, design: .default, weight: .regular)// 15
        static let footnote = Font.system(.footnote, design: .default, weight: .regular)  // 13
        static let caption = Font.system(.caption2, design: .default, weight: .regular)   // 11

        static func mono(_ style: Font.TextStyle = .body, weight: Font.Weight = .regular) -> Font {
            Font.system(style, design: .monospaced, weight: weight)
        }
    }

    /// cubic-bezier(0.22, 1, 0.36, 1) · 160ms / 280ms
    enum Motion {
        static let fast = Animation.timingCurve(0.22, 1, 0.36, 1, duration: 0.16)
        static let medium = Animation.timingCurve(0.22, 1, 0.36, 1, duration: 0.28)
    }

    /// Lulu 出场尺寸（pt）
    enum LuluSize {
        static let hero: CGFloat = 260      // 主场景 240–300
        static let header: CGFloat = 120    // 页面头部 96–140
        static let empty: CGFloat = 170     // 空态 / 错误态 140–190
        static let confirm: CGFloat = 84    // 确认卡 72–96
        static let avatar: CGFloat = 44     // 消息头像 36–48
    }
}

extension Color {
    init(hex: UInt32, alpha: Double = 1) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255,
            opacity: alpha
        )
    }
}

/// 页面画布：纯暖纸色，无渐变、无发光。
struct OMPageBackground: View {
    var body: some View {
        OMTheme.ColorToken.paper.ignoresSafeArea()
    }
}

extension View {
    func omPageStyle() -> some View {
        background(OMPageBackground())
            .foregroundStyle(OMTheme.ColorToken.ink)
            .tint(OMTheme.ColorToken.ink)
            .preferredColorScheme(.light)
    }
}
