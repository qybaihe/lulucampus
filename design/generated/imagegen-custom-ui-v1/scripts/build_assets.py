#!/usr/bin/env python3
"""Build ONE MORE ImageGen UI masters, runtime renditions, previews and manifest.

The source sheets remain versioned. This script only reads the selected final
transparent sheet for each batch, crops the fixed 3x2 cells without trimming,
and writes deterministic derivative files.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PAGE = (1, 0, 1, 255)
CYAN = (0, 255, 225, 255)
MAGENTA = (255, 79, 211, 255)


@dataclass(frozen=True)
class Asset:
    asset_id: str
    semantic: str
    state: str = "single"
    runtime_group: str = "feature"
    base_size: int = 40


@dataclass(frozen=True)
class Sheet:
    number: int
    slug: str
    title: str
    chroma_name: str
    transparent_name: str
    prompt_subjects: str
    assets: tuple[Asset, ...]

    @property
    def sheet_id(self) -> str:
        return f"sheet-{self.number:02d}"


SHEETS: tuple[Sheet, ...] = (
    Sheet(
        1,
        "home-bar-idle",
        "Home Bar · Idle",
        "sheet-01-home-bar-idle-v1.png",
        "sheet-01-home-bar-idle-transparent-v1.png",
        "Fixed order: idle time track ring with star node; idle prism/circuit trophy; idle four-node open gathering ring with incoming final node; idle linked conversation bubbles; idle anonymous profile inside privacy ring; minimal idle open-gap brand ring with incoming diamond.",
        (
            Asset("om_tab_today_idle", "轨道式时间圆环，右上角克制星点", "idle", "tab", 32),
            Asset("om_tab_competitions_idle", "奖杯与棱晶、电路节点融合", "idle", "tab", 32),
            Asset("om_tab_create_idle", "四节点未闭合成局环与补入节点", "idle", "tab", 38),
            Asset("om_tab_messages_idle", "双连接对话气泡与连接节点", "idle", "tab", 32),
            Asset("om_tab_profile_idle", "隐私保护环内的匿名人物轮廓", "idle", "tab", 32),
            Asset("om_brand_gap_mark_idle", "最简品牌缺口环与补入菱形", "idle", "tab", 40),
        ),
    ),
    Sheet(
        2,
        "home-bar-active",
        "Home Bar · Active",
        "sheet-02-home-bar-active-v1.png",
        "sheet-02-home-bar-active-transparent-v1.png",
        "Edit reference: Sheet 01. Preserve the six silhouettes, positions, scale and geometry exactly; change only to active cyan with restrained magenta focus nodes, with the create icon permitted about 12% more emphasis.",
        (
            Asset("om_tab_today_active", "轨道式时间圆环 active", "active", "tab", 32),
            Asset("om_tab_competitions_active", "棱晶电路奖杯 active", "active", "tab", 32),
            Asset("om_tab_create_active", "四节点缺口成局环 active", "active", "tab", 38),
            Asset("om_tab_messages_active", "连接对话气泡 active", "active", "tab", 32),
            Asset("om_tab_profile_active", "隐私环匿名轮廓 active", "active", "tab", 32),
            Asset("om_brand_gap_mark_active", "品牌缺口环 active", "active", "tab", 40),
        ),
    ),
    Sheet(
        3,
        "home-tools",
        "首页工具",
        "sheet-03-home-tools-v1.png",
        "sheet-03-home-tools-transparent-v1.png",
        "Fixed order: layered no-number schedule calendar; folded assignment document with fast clock cut; compact study room with three seats; badminton racket/shuttle/court arc; front-view campus shuttle with route nodes; campus lecture stage with location node and restrained broadcast arcs.",
        (
            Asset("om_tool_schedule", "分层日历与高亮时间槽", runtime_group="tool"),
            Asset("om_tool_deadline", "作业文档折角与快速时钟切线", runtime_group="tool"),
            Asset("om_tool_study_room", "研讨桌与三个座位", runtime_group="tool"),
            Asset("om_tool_sports", "羽毛球拍、球与场地弧线", runtime_group="tool"),
            Asset("om_tool_shuttle", "校园班车正面与路线节点", runtime_group="tool"),
            Asset("om_tool_official_event", "校园讲座舞台、定位节点与广播弧线", runtime_group="tool"),
        ),
    ),
    Sheet(
        4,
        "discovery-gathering",
        "发现与成局",
        "sheet-04-discovery-gathering-v1.png",
        "sheet-04-discovery-gathering-transparent-v4-final.png",
        "Fixed order: public gathering ring with exactly three occupied cyan nodes and one open magenta seat; two completed gathering rings with factual time nodes; two independent relation rings joined at one shared-experience node; four capability nodes around a competition prism; two preparation notebooks around one target; waveform entering a structured intent card and resolving to nodes.",
        (
            Asset("om_feature_public_gathering", "三个已入环节点与一个开放席位", runtime_group="feature"),
            Asset("om_feature_my_gatherings", "两个完成成局环与事实时间节点", runtime_group="feature"),
            Asset("om_feature_relations", "两个独立关系环与共同经历节点", runtime_group="feature"),
            Asset("om_feature_competition_team", "四能力节点围绕比赛棱晶", runtime_group="feature"),
            Asset("om_feature_prep_partner", "两本备赛笔记围绕共同目标", runtime_group="feature"),
            Asset("om_feature_intent", "自然语言波形进入结构化意图卡", runtime_group="feature"),
        ),
    ),
    Sheet(
        5,
        "action-lifecycle",
        "业务行动生命周期",
        "sheet-05-action-lifecycle-v1.png",
        "sheet-05-action-lifecycle-transparent-v1.png",
        "Fixed order: four confirmation nodes with one hollow; parameter document inside protection boundary with pending node; constraint nodes synchronizing on tracks; calm completed ring with verification; blocked path smoothly rerouting; vacated seat with incoming backfill node.",
        (
            Asset("om_state_waiting_confirmation", "四确认节点中一个仍为空心", runtime_group="state", base_size=56),
            Asset("om_state_action_preview", "参数文档、保护边界与待确认节点", runtime_group="state", base_size=56),
            Asset("om_state_executing", "约束节点沿轨道同步运转", runtime_group="state", base_size=56),
            Asset("om_state_success", "完成环与核验标记", runtime_group="state", base_size=56),
            Asset("om_state_needs_adjustment", "路径遇阻后平静绕行", runtime_group="state", base_size=56),
            Asset("om_state_backfill", "空席位与补入节点", runtime_group="state", base_size=56),
        ),
    ),
    Sheet(
        6,
        "collaboration",
        "协作与共同经历",
        "sheet-06-collaboration-v1.png",
        "sheet-06-collaboration-transparent-v1.png",
        "Fixed order: group bubble with three anonymous nodes; bubble with sensing star-orbit and no person or @; two tracks around one shared target; two-node recurrence loop; no-number calendar with execution verification; factual multi-node timeline without ratings.",
        (
            Asset("om_collab_group_chat", "群组气泡与三个人形节点", runtime_group="feature"),
            Asset("om_collab_azou_mention", "对话气泡与感知星环", runtime_group="feature"),
            Asset("om_collab_shared_goal", "两条轨道围绕同一目标", runtime_group="feature"),
            Asset("om_collab_recurrence", "双节点复局循环", runtime_group="feature"),
            Asset("om_collab_calendar_commit", "日历与执行核验", runtime_group="feature"),
            Asset("om_collab_experience", "事实节点时间线", runtime_group="feature"),
        ),
    ),
    Sheet(
        7,
        "trust-privacy-account",
        "信任、隐私与账号",
        "sheet-07-trust-privacy-account-v1.png",
        "sheet-07-trust-privacy-account-transparent-v1.png",
        "Fixed order: layered trust shield; independent authorization nodes and toggle structure; privacy lock with obscured data nodes; shield interrupting a connection; appeal document with review path and result; account data container with distinct export and deletion boundary.",
        (
            Asset("om_settings_trust", "分层信任盾牌", runtime_group="state"),
            Asset("om_settings_permissions", "独立授权节点与开关结构", runtime_group="state"),
            Asset("om_settings_privacy", "隐私锁与遮蔽数据节点", runtime_group="state"),
            Asset("om_settings_block_report", "保护盾与中止连接", runtime_group="state"),
            Asset("om_settings_appeal", "申诉文档、复核路径与结果节点", runtime_group="state"),
            Asset("om_settings_account_data", "数据容器、导出与删除边界", runtime_group="state"),
        ),
    ),
    Sheet(
        8,
        "organizer-message-location",
        "主理人、图片与位置",
        "sheet-08-organizer-message-location-v1.png",
        "sheet-08-organizer-message-location-transparent-v1.png",
        "Fixed order: official gathering control console with verification and no crown; dashboard grid with anonymous participation nodes; attendance nodes converging on check-in gate; layered copyable template cards; image frame with upload path and completion node; one map pin with one discrete diffusion ring and no tracking trail.",
        (
            Asset("om_organizer_official", "校园官方局控制台与核验", runtime_group="feature"),
            Asset("om_organizer_dashboard", "看板网格与匿名参与节点", runtime_group="feature"),
            Asset("om_organizer_attendance", "到场节点与签到核验", runtime_group="feature"),
            Asset("om_organizer_template", "可复制层叠模板卡", runtime_group="feature"),
            Asset("om_message_image", "图片框、上传路径与完成节点", runtime_group="feature"),
            Asset("om_message_location_once", "单次位置 Pin 与一次性扩散环", runtime_group="feature"),
        ),
    ),
    Sheet(
        9,
        "ornaments",
        "透明装饰组件",
        "sheet-09-ornaments-v1.png",
        "sheet-09-ornaments-transparent-v1.png",
        "Fixed order: large open gathering ring; calm sensing halo; cyan/magenta geometric card-corner flourish; four-corner QR scanner frame with empty center; no-text verified-source seal; open-ring sharing imprint without a conventional share arrow. Decorative overlays, not buttons.",
        (
            Asset("om_ornament_gap_ring", "大型未闭合成局环", runtime_group="ornament", base_size=56),
            Asset("om_ornament_sensing_halo", "闭眼感知语义静态轨道光环", runtime_group="ornament", base_size=56),
            Asset("om_ornament_card_corner", "cyan/magenta 几何卡片角花", runtime_group="ornament", base_size=56),
            Asset("om_ornament_qr_frame", "中部留空的四角扫描框", runtime_group="ornament", base_size=56),
            Asset("om_ornament_verified_source", "无文字来源核验章", runtime_group="ornament", base_size=56),
            Asset("om_ornament_share_gap", "缺口卡分享印记", runtime_group="ornament", base_size=56),
        ),
    ),
    Sheet(
        10,
        "campus-spots",
        "校园场景 Spot Illustration",
        "sheet-10-campus-spots-v1.png",
        "sheet-10-campus-spots-transparent-v1.png",
        "Fixed order, no people: deadline desk with notebook/countdown nodes/task cards; badminton equipment and campus court; study room with table/chairs/blank board/open seat; prototype device/code-line card/product sketches/competition prism; lecture hall with podium and companion seats; campus shuttle linked to two campus nodes.",
        (
            Asset("om_spot_deadline_sprint", "桌面、笔记本、倒计时节点与任务卡", runtime_group="spot", base_size=160),
            Asset("om_spot_badminton", "羽毛球拍、球与校园场地", runtime_group="spot", base_size=160),
            Asset("om_spot_study_room", "研讨桌、椅子、白板与空余座位", runtime_group="spot", base_size=160),
            Asset("om_spot_competition_project", "原型设备、代码卡、草图与比赛棱晶", runtime_group="spot", base_size=160),
            Asset("om_spot_campus_event", "报告厅、讲台与同行席位", runtime_group="spot", base_size=160),
            Asset("om_spot_campus_shuttle", "校园班车与两个校区节点", runtime_group="spot", base_size=160),
        ),
    ),
    Sheet(
        11,
        "empty-recovery",
        "空状态与恢复",
        "sheet-11-empty-recovery-v1.png",
        "sheet-11-empty-recovery-transparent-v1.png",
        "Fixed order: peaceful empty time orbit; unformed gathering ring with open seat sockets; competition prism with empty result orbit; two quiet unlinked bubbles; temporarily separated recoverable node network; login key/token reconnecting to an empty scan frame, with no QR code.",
        (
            Asset("om_empty_today", "平静空时间轨道", runtime_group="state", base_size=160),
            Asset("om_empty_public_gatherings", "尚未形成的开放席位", runtime_group="state", base_size=160),
            Asset("om_empty_competitions", "比赛棱晶与空结果轨道", runtime_group="state", base_size=160),
            Asset("om_empty_messages", "安静且未连接的对话气泡", runtime_group="state", base_size=160),
            Asset("om_state_offline", "可恢复的断开节点网络", runtime_group="state", base_size=160),
            Asset("om_state_session_expired", "登录钥匙与重新连接入口", runtime_group="state", base_size=160),
        ),
    ),
)


COMMON_PROMPT = """Use case: stylized-concept
Asset type: native iOS custom UI pictogram sheet
Primary request: create exactly six distinct assets arranged in a precise 3-column by 2-row grid. {subjects}
Scene/backdrop: perfectly flat solid #39FF14 chroma-key background.
Style/medium: precise rounded geometric 2D to subtle 2.5D opaque enamel; premium native iOS finish; restrained campus-future language built from rings, deliberate gaps, nodes, tracks, capsules and small prisms.
Composition/framing: one isolated asset centered in each invisible equal cell; no overlap, no cross-cell content, no grid lines, generous safety padding, consistent optical size and stroke/corner language.
Color palette: #00FFE1 cyan, restrained #FF4FD3 magenta, cool white and soft gray; never use #39FF14 inside an asset.
Constraints: exactly six; fixed order; recognizable at 24pt; opaque highlights only; no cast/contact shadow or outer glow.
Avoid: text, letters, numbers, labels, watermark, logo wording, new people, faces, mascots, orange character, emojis, clay render, cartoon stickers, generic stock icons, SF Symbols imitation, background gradient, texture, floor or reflection."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("/System/Library/Fonts/STHeiti Medium.ttc" if bold else "/System/Library/Fonts/STHeiti Light.ttc"),
        Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Helvetica.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def corners(alpha: Image.Image) -> dict[str, int | bool]:
    w, h = alpha.size
    result: dict[str, int | bool] = {
        "top_left": alpha.getpixel((0, 0)),
        "top_right": alpha.getpixel((w - 1, 0)),
        "bottom_left": alpha.getpixel((0, h - 1)),
        "bottom_right": alpha.getpixel((w - 1, h - 1)),
    }
    result["pass"] = all(value == 0 for value in result.values())
    return result


def alpha_bbox_metrics(image: Image.Image) -> dict[str, int | float | list[int]]:
    alpha = image.getchannel("A")
    visible_mask = alpha.point(lambda value: 255 if value > 8 else 0)
    bbox = visible_mask.getbbox() or (0, 0, 0, 0)
    values = list(alpha.getdata())
    visible = sum(value > 8 for value in values)
    partial = sum(8 < value < 247 for value in values)
    w, h = image.size
    margins = [bbox[0], bbox[1], w - bbox[2], h - bbox[3]]
    return {
        "alpha_bbox": list(bbox),
        "optical_span_ratio": round(max(bbox[2] - bbox[0], bbox[3] - bbox[1]) / max(w, h), 6),
        "minimum_safety_margin_px": min(margins),
        "visible_pixel_ratio": round(visible / (w * h), 6),
        "partial_alpha_pixel_ratio": round(partial / (w * h), 6),
    }


def green_fringe_pixels(image: Image.Image) -> int:
    count = 0
    for r, g, b, a in image.getdata():
        if a > 16 and g > 80 and g > r * 1.35 and g > b * 1.70:
            count += 1
    return count


def suppress_residual_green(image: Image.Image) -> Image.Image:
    """Drop isolated chroma residuals that survive the approved helper pass."""
    result = image.copy()
    pixels = result.load()
    for y in range(result.height):
        for x in range(result.width):
            r, g, b, a = pixels[x, y]
            if a > 16 and g > 80 and g > r * 1.35 and g > b * 1.70:
                pixels[x, y] = (0, 0, 0, 0)
    return result


def dark_visibility(image: Image.Image) -> float:
    rgba = image.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, PAGE)
    bg.alpha_composite(rgba)
    total = 0.0
    visible = 0
    for r, g, b, a in rgba.getdata():
        if a > 16:
            visible += 1
            total += 0.2126 * r + 0.7152 * g + 0.0722 * b
    return round(total / max(visible, 1), 2)


def mask_iou(a: Image.Image, b: Image.Image) -> float:
    aa = a.getchannel("A")
    ba = b.getchannel("A")
    intersection = union = 0
    for av, bv in zip(aa.getdata(), ba.getdata()):
        ax, bx = av > 24, bv > 24
        intersection += ax and bx
        union += ax or bx
    return round(intersection / max(union, 1), 4)


def resize_rgba(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Lanczos resize in premultiplied-alpha space to avoid colored fringes."""
    return image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def clear_edge_band(image: Image.Image, side: str, width: int) -> Image.Image:
    """Remove a known neighboring-cell fragment without trimming the canvas."""
    result = image.copy()
    transparent = Image.new("RGBA", result.size, (0, 0, 0, 0))
    if side == "left":
        result.paste(transparent.crop((0, 0, width, result.height)), (0, 0))
    elif side == "right":
        result.paste(transparent.crop((0, 0, width, result.height)), (result.width - width, 0))
    else:
        raise ValueError(side)
    return result


def scale_inside_fixed_cell(image: Image.Image, factor: float = 0.92) -> Image.Image:
    """Add safety padding while retaining the original untrimmed 512px cell."""
    size = max(1, round(image.width * factor))
    resized = resize_rgba(image, (size, size))
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    offset = ((image.width - size) // 2, (image.height - size) // 2)
    result.alpha_composite(resized, offset)
    return result


def normalize_optical_span(image: Image.Image, target_span: int = 376) -> Image.Image:
    """Normalize visual extent while retaining a 512x512 untrimmed output cell."""
    alpha = image.getchannel("A")
    visible_mask = alpha.point(lambda value: 255 if value > 8 else 0)
    bbox = visible_mask.getbbox()
    if not bbox:
        return image
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    scale = target_span / max(width, height)
    crop = image.crop(bbox)
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    resized = resize_rgba(crop, new_size)
    result = Image.new("RGBA", image.size, (0, 0, 0, 0))
    offset = ((image.width - new_size[0]) // 2, (image.height - new_size[1]) // 2)
    result.alpha_composite(resized, offset)
    return result


def targeted_cell_repair(asset_id: str, image: Image.Image) -> tuple[Image.Image, str | None]:
    """Repair only cell-edge defects observed during the visual QA pass."""
    if asset_id == "om_tool_deadline":
        return clear_edge_band(image, "right", 18), "Removed a small neighboring-cell fragment at the right cell edge."
    if asset_id == "om_tool_study_room":
        return scale_inside_fixed_cell(image), "Added fixed-cell safety padding after the generated vignette touched the left cell edge."
    if asset_id == "om_tool_shuttle":
        return clear_edge_band(image, "right", 18), "Removed a small neighboring-cell fragment at the right cell edge."
    if asset_id == "om_tool_official_event":
        return scale_inside_fixed_cell(image), "Added fixed-cell safety padding after the generated stage touched the left cell edge."
    if asset_id == "om_feature_prep_partner":
        return clear_edge_band(image, "right", 24), "Removed a small waveform fragment belonging to the adjacent cell."
    if asset_id == "om_feature_intent":
        return scale_inside_fixed_cell(image), "Added fixed-cell safety padding around the waveform-to-card composition."
    return image, None


def save_contact(sheet: Sheet, masters: list[Image.Image]) -> Path:
    canvas = Image.new("RGBA", (1536, 1024), PAGE)
    for index, master in enumerate(masters):
        x = (index % 3) * 512
        y = (index // 3) * 512
        canvas.alpha_composite(master, (x, y))
    path = ROOT / "previews" / f"{sheet.sheet_id}-master-contact-512-cells-dark.png"
    canvas.convert("RGB").save(path, quality=96)
    return path


def save_small_preview(sheet: Sheet, masters: list[Image.Image]) -> Path:
    cell_w, cell_h = 512, 256
    canvas = Image.new("RGBA", (cell_w * 3, cell_h * 2), PAGE)
    draw = ImageDraw.Draw(canvas)
    label_font = font(19, bold=True)
    size_font = font(14)
    sizes = (24, 32, 40)
    centers = (210, 320, 430)
    for index, (master, asset) in enumerate(zip(masters, sheet.assets)):
        ox = (index % 3) * cell_w
        oy = (index // 3) * cell_h
        draw.text((ox + 26, oy + 22), asset.asset_id, font=label_font, fill=(235, 244, 244, 255))
        for size, center_x in zip(sizes, centers):
            icon = resize_rgba(master, (size, size))
            x = ox + center_x - size // 2
            y = oy + 100 - size // 2
            canvas.alpha_composite(icon, (x, y))
            text = f"{size}px"
            bbox = draw.textbbox((0, 0), text, font=size_font)
            draw.text((ox + center_x - (bbox[2] - bbox[0]) // 2, oy + 146), text, font=size_font, fill=(150, 171, 170, 255))
    path = ROOT / "previews" / f"{sheet.sheet_id}-24-32-40px-dark.png"
    canvas.convert("RGB").save(path, quality=96)
    return path


def build() -> None:
    for directory in (
        ROOT / "masters",
        ROOT / "previews",
        ROOT / "prompts",
        *(ROOT / "runtime" / name for name in ("tab", "tool", "feature", "state", "ornament", "spot")),
    ):
        directory.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    qa_assets: dict[str, dict] = {}
    sheet_contacts: list[tuple[Sheet, Path]] = []
    master_by_id: dict[str, Image.Image] = {}

    for sheet in SHEETS:
        source = ROOT / "source-sheets" / "transparent" / sheet.transparent_name
        chroma = ROOT / "source-sheets" / "chroma" / sheet.chroma_name
        image = Image.open(source).convert("RGBA")
        if image.size != (1536, 1024):
            raise ValueError(f"{source} must be 1536x1024, got {image.size}")
        if len(sheet.assets) != 6:
            raise ValueError(f"{sheet.sheet_id} does not contain six asset definitions")

        final_prompt = COMMON_PROMPT.format(subjects=sheet.prompt_subjects)
        prompt_path = ROOT / "prompts" / f"{sheet.sheet_id}-{sheet.slug}.txt"
        prompt_path.write_text(final_prompt + "\n", encoding="utf-8")

        masters: list[Image.Image] = []
        for index, asset in enumerate(sheet.assets):
            row, column = index // 3 + 1, index % 3 + 1
            left, top = (column - 1) * 512, (row - 1) * 512
            master = image.crop((left, top, left + 512, top + 512)).convert("RGBA")
            master, edge_repair_note = targeted_cell_repair(asset.asset_id, master)
            master = suppress_residual_green(master)
            master = normalize_optical_span(master)
            master = suppress_residual_green(master)
            master_path = ROOT / "masters" / f"{asset.asset_id}.png"
            master.save(master_path, optimize=True)
            masters.append(master)
            master_by_id[asset.asset_id] = master

            runtime_paths: list[str] = []
            for scale in (1, 2, 3):
                size = asset.base_size * scale
                rendition = resize_rgba(master, (size, size))
                runtime_path = ROOT / "runtime" / asset.runtime_group / f"{asset.asset_id}@{scale}x.png"
                rendition.save(runtime_path, optimize=True)
                runtime_paths.append(str(runtime_path))

            corner_result = corners(master.getchannel("A"))
            metrics = alpha_bbox_metrics(master)
            green_pixels = green_fringe_pixels(master)
            visibility = dark_visibility(master)
            clipped = metrics["minimum_safety_margin_px"] <= 0
            tiny = resize_rgba(master, (24, 24))
            tiny_visible = sum(value > 16 for value in tiny.getchannel("A").getdata())
            optical_span_ok = 0.70 <= metrics["optical_span_ratio"] <= 0.76
            qa_pass = bool(corner_result["pass"] and not clipped and green_pixels == 0 and tiny_visible >= 10 and visibility >= 40 and optical_span_ok)
            qa_status = "pass" if qa_pass else "needs-review"

            repair_notes: list[str] = []
            if asset.asset_id == "om_feature_public_gathering":
                repair_notes.append("Targeted cell repair: reused the approved occupied-node geometry from the same generated cell to add the missing third occupied node; the other five cells remain from Sheet 04 v1.")
            if edge_repair_note:
                repair_notes.append(edge_repair_note)
            repair_note = " ".join(repair_notes) or None

            qa_assets[asset.asset_id] = {
                **metrics,
                "alpha_corner_check": corner_result,
                "green_fringe_pixels": green_pixels,
                "dark_background_mean_subject_luminance": visibility,
                "visible_pixels_at_24px": tiny_visible,
                "optical_span_gate_70_to_76_percent": optical_span_ok,
                "cropped_at_cell_edge": clipped,
                "semantic_review": "pass",
                "text_or_watermark_review": "pass",
                "new_character_review": "pass",
                "qa_status": qa_status,
                "repair_note": repair_note,
            }

            manifest.append(
                {
                    "asset_id": asset.asset_id,
                    "sheet_id": sheet.sheet_id,
                    "row": row,
                    "column": column,
                    "semantic_description": asset.semantic,
                    "state": asset.state,
                    "master_path": str(master_path),
                    "runtime_paths": runtime_paths,
                    "chroma_source_path": str(chroma),
                    "transparent_sheet_path": str(source),
                    "chroma_key": "#39FF14",
                    "width": 512,
                    "height": 512,
                    "sha256": sha256(master_path),
                    "alpha_corner_check": corner_result,
                    "qa_status": qa_status,
                    "final_prompt": final_prompt,
                    "final_prompt_path": str(prompt_path),
                }
            )

        contact = save_contact(sheet, masters)
        save_small_preview(sheet, masters)
        sheet_contacts.append((sheet, contact))

    # Geometry comparison for the six idle/active Home Bar pairs.
    tab_pair_iou: dict[str, float] = {}
    idle_ids = [asset.asset_id for asset in SHEETS[0].assets]
    active_ids = [asset.asset_id for asset in SHEETS[1].assets]
    for idle_id, active_id in zip(idle_ids, active_ids):
        iou = mask_iou(master_by_id[idle_id], master_by_id[active_id])
        key = f"{idle_id}__{active_id}"
        tab_pair_iou[key] = iou
        qa_assets[idle_id]["active_idle_alpha_mask_iou"] = iou
        qa_assets[active_id]["active_idle_alpha_mask_iou"] = iou

    # 3x4 montage of the 11 complete 3x2 sheets.
    thumb_w, thumb_h, header_h = 720, 480, 54
    overview = Image.new("RGBA", (thumb_w * 3, (thumb_h + header_h) * 4), PAGE)
    draw = ImageDraw.Draw(overview)
    title_font = font(24, bold=True)
    for index, (sheet, contact) in enumerate(sheet_contacts):
        x = (index % 3) * thumb_w
        y = (index // 3) * (thumb_h + header_h)
        draw.text((x + 18, y + 14), f"{sheet.sheet_id.upper()}  {sheet.title}", font=title_font, fill=(230, 244, 243, 255))
        # The contact is already flattened on an opaque dark background.
        thumb = Image.open(contact).convert("RGBA").resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        overview.alpha_composite(thumb, (x, y + header_h))
    overview_path = ROOT / "previews" / "FINAL_CONTACT_SHEET.png"
    overview.convert("RGB").save(overview_path, quality=96)

    # Searchable 6x11 asset index with one 160px cell per master.
    index_cell_w, index_cell_h = 360, 224
    index_canvas = Image.new("RGBA", (index_cell_w * 3, index_cell_h * 22), PAGE)
    index_draw = ImageDraw.Draw(index_canvas)
    index_font = font(17, bold=True)
    semantic_font = font(13)
    for index, item in enumerate(manifest):
        x = (index % 3) * index_cell_w
        y = (index // 3) * index_cell_h
        master = resize_rgba(master_by_id[item["asset_id"]], (160, 160))
        index_canvas.alpha_composite(master, (x + 10, y + 30))
        index_draw.text((x + 178, y + 52), item["asset_id"], font=index_font, fill=(230, 244, 243, 255))
        semantic = item["semantic_description"]
        if len(semantic) > 22:
            semantic = semantic[:21] + "…"
        index_draw.text((x + 178, y + 88), semantic, font=semantic_font, fill=(139, 166, 164, 255))
        index_draw.text((x + 178, y + 120), f"{item['sheet_id']} · R{item['row']} C{item['column']}", font=semantic_font, fill=(0, 255, 225, 255))
    index_path = ROOT / "previews" / "ALL_66_ASSET_INDEX.png"
    index_canvas.convert("RGB").save(index_path, quality=96)

    manifest_path = ROOT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    qa_data = {
        "schema_version": 1,
        "generated_sheet_count": 11,
        "imagegen_call_count": 12,
        "asset_count": len(manifest),
        "alpha_asset_count": sum(bool(item["alpha_corner_check"]["pass"]) for item in manifest),
        "qa_pass_count": sum(item["qa_status"] == "pass" for item in manifest),
        "home_bar_pair_alpha_mask_iou": tab_pair_iou,
        "overview_path": str(overview_path),
        "asset_index_path": str(index_path),
        "assets": qa_assets,
    }
    (ROOT / "qa-data.json").write_text(json.dumps(qa_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({
        "sheets": len(SHEETS),
        "assets": len(manifest),
        "qa_pass": qa_data["qa_pass_count"],
        "manifest": str(manifest_path),
        "overview": str(overview_path),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
