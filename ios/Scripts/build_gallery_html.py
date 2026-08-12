#!/usr/bin/env python3
"""把 artifacts/screenshots/gallery/*.png 生成可用浏览器翻阅的 HTML 画廊。"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GALLERY = ROOT / "artifacts" / "screenshots" / "gallery"
OUT = GALLERY / "index.html"

TITLES = {
    "A1": "启动路由", "A2": "认证说明", "A3": "扫码认证", "A4": "授权范围",
    "A5": "画像初始化", "A6": "画像确认", "A7": "社交开关", "A8": "系统权限",
    "B1": "今天", "B2": "Lulu Hermes 问答", "B3": "我的课表", "B3.1": "课程详情",
    "B4": "作业与 DDL", "B4.1": "作业详情", "B5": "体育场馆", "B5.1": "体育时段",
    "B6": "研讨室", "B6.1": "研讨室时段", "B7": "校园活动", "B7.1": "活动详情",
    "B8": "组会与课题", "B9": "班车与节次", "B10": "场景触发", "B11": "个人行动预览",
    "B12": "比赛雷达", "B12.1": "赛事详情",
    "C1": "公开局", "C2": "公开局详情", "C3": "准入门槛", "C4": "缺口卡落地",
    "D1": "意图输入", "D2": "澄清追问", "D3": "意图卡确认", "D3.1": "能力编辑",
    "D3.2": "空档选择", "D3.3": "角色编辑", "D3.4": "安全偏好", "D4": "匿名池",
    "E1": "我的局", "E2": "局详情", "E3": "多人确认", "E4": "改约协商",
    "E5": "行动预览", "E6": "执行结果", "E7": "协作空间", "E8": "补位",
    "E9": "完成确认", "E10": "复局选择", "E11": "共同目标", "E12": "退出",
    "E13": "举报与拉黑", "E14": "局内群聊", "E15": "搭子关系", "E16": "共同经历",
    "E17": "解除关系",
    "M1": "个人中心", "M2": "画像编辑", "M3": "信任进度", "M4": "授权管理",
    "M5": "隐私与安全", "M6": "匹配偏好", "M7": "通知与日历", "M8": "黑名单",
    "M9": "信任申诉", "M10": "账号与数据",
    "O1": "主理人控制台", "O2": "创建官方局", "O3": "报名与到场看板", "O4": "官方局模板",
    "G1": "Lulu Hermes 唤起", "G2": "缺口卡分享", "G3": "认证恢复", "G4": "静默解散", "G5": "状态规范",
    "TAB-today": "今天", "TAB-competitions": "活动", "TAB-create": "差一个",
    "TAB-messages": "消息", "TAB-profile": "我",
}

SECTIONS = [
    ("主导航 · 五个 Tab", ["TAB-today", "TAB-competitions", "TAB-create", "TAB-messages", "TAB-profile"]),
    ("A · 启动与认证", [f"A{i}" for i in range(1, 9)]),
    ("B · 今天与校园", ["B1", "B2", "B3", "B3.1", "B4", "B4.1", "B5", "B5.1", "B6", "B6.1",
                        "B7", "B7.1", "B8", "B9", "B10", "B11", "B12", "B12.1"]),
    ("C · 公开局", ["C1", "C2", "C3", "C4"]),
    ("D · 意图与发布", ["D1", "D2", "D3", "D3.1", "D3.2", "D3.3", "D3.4", "D4"]),
    ("E · 局与关系", [f"E{i}" for i in range(1, 18)]),
    ("M · 我的", [f"M{i}" for i in range(1, 11)]),
    ("O · 主理人", [f"O{i}" for i in range(1, 5)]),
    ("G · 全局与分享", [f"G{i}" for i in range(1, 6)]),
]

CSS = """
:root {
  --paper:#f6f4ec; --ink:#1f2d25; --yolk:#f6c945; --card:#fffdf8;
  --mist:#5d6b63; --line:#dce3d9; --sage:#cbd4cc;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--paper); color:var(--ink);
  font-family:-apple-system,"PingFang SC","Helvetica Neue",sans-serif; }
header { padding:48px 40px 8px; }
header .eyebrow { font-size:13px; font-weight:700; letter-spacing:2.5px; color:var(--mist); }
header h1 { font-size:34px; font-weight:800; letter-spacing:-0.5px; margin-top:6px; }
header p { color:var(--mist); font-size:14px; margin-top:8px; }
nav { position:sticky; top:0; z-index:10; background:color-mix(in srgb,var(--paper) 88%, transparent);
  backdrop-filter:blur(12px); padding:12px 40px; display:flex; flex-wrap:wrap; gap:8px;
  border-bottom:1px solid var(--line); }
nav a { font-size:13px; font-weight:600; color:var(--ink); text-decoration:none;
  padding:6px 14px; border:1px solid var(--line); border-radius:999px; background:var(--card); }
nav a:hover { background:var(--yolk); border-color:var(--ink); }
section { padding:32px 40px 8px; }
section h2 { font-size:20px; font-weight:800; margin-bottom:4px; }
section .desc { color:var(--mist); font-size:13px; margin-bottom:18px; }
.grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:22px; }
.shot { background:var(--card); border:1px solid var(--line); border-radius:20px;
  padding:12px; transition:transform .16s cubic-bezier(.22,1,.36,1), box-shadow .16s; }
.shot:hover { transform:translateY(-3px); box-shadow:0 10px 28px rgba(31,45,37,.10); }
.shot img { width:100%; border-radius:12px; border:1px solid var(--line); display:block;
  cursor:zoom-in; background:#eee; }
.shot .meta { display:flex; align-items:baseline; gap:8px; padding:10px 4px 2px; }
.shot .id { font-size:12px; font-weight:800; background:var(--yolk); border-radius:6px;
  padding:2px 7px; letter-spacing:.5px; }
.shot .title { font-size:13px; font-weight:600; }
.shot.missing { opacity:.45; }
.shot.missing .ph { aspect-ratio:1179/2556; border-radius:12px; border:1.5px dashed var(--sage);
  display:flex; align-items:center; justify-content:center; color:var(--mist); font-size:12px; }
#lightbox { position:fixed; inset:0; background:rgba(31,45,37,.82); display:none;
  align-items:center; justify-content:center; z-index:99; cursor:zoom-out; }
#lightbox img { max-height:94vh; max-width:92vw; border-radius:18px; }
#lightbox.open { display:flex; }
footer { padding:36px 40px 56px; color:var(--mist); font-size:12px; }
"""

JS = """
const lb = document.getElementById('lightbox');
const lbImg = lb.querySelector('img');
document.querySelectorAll('.shot img').forEach(img => {
  img.addEventListener('click', () => { lbImg.src = img.src; lb.classList.add('open'); });
});
lb.addEventListener('click', () => lb.classList.remove('open'));
document.addEventListener('keydown', e => { if (e.key === 'Escape') lb.classList.remove('open'); });
"""


def anchor(name: str) -> str:
    return name.replace(" ", "-").replace("·", "").strip("-")


def main() -> None:
    parts = [
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        "<title>ONE MORE · 全量 UI 画廊</title>",
        f"<style>{CSS}</style></head><body>",
        "<header><div class='eyebrow'>ONE MORE · LULU 亮色设计稿</div>",
        "<h1>全量 UI 截图画廊</h1>",
        f"<p>生产页面实拍（模拟器 iPhone 15 Pro · 演示数据）· 共 {sum(len(s[1]) for s in SECTIONS)} 屏 · 点击任意截图放大</p></header>",
        "<nav>",
    ]
    for name, _ in SECTIONS:
        parts.append(f"<a href='#{anchor(name)}'>{name}</a>")
    parts.append("</nav>")

    total_shots = 0
    for name, ids in SECTIONS:
        parts.append(f"<section id='{anchor(name)}'><h2>{name}</h2>")
        parts.append(f"<div class='desc'>{len(ids)} 屏</div><div class='grid'>")
        for node in ids:
            png = GALLERY / f"{node}.png"
            title = TITLES.get(node, "")
            if png.exists():
                total_shots += 1
                parts.append(
                    f"<div class='shot'><img src='{node}.png' loading='lazy' alt='{node} {title}'>"
                    f"<div class='meta'><span class='id'>{node.replace('TAB-', '')}</span>"
                    f"<span class='title'>{title}</span></div></div>"
                )
            else:
                parts.append(
                    f"<div class='shot missing'><div class='ph'>未捕获</div>"
                    f"<div class='meta'><span class='id'>{node}</span>"
                    f"<span class='title'>{title}</span></div></div>"
                )
        parts.append("</div></section>")

    parts.append(f"<footer>ONE MORE · 生成于构建流水线 · 实拍到账 {total_shots} 屏</footer>")
    parts.append(f"<div id='lightbox'><img src='' alt=''></div><script>{JS}</script>")
    parts.append("</body></html>")
    OUT.write_text("".join(parts), encoding="utf-8")
    print(f"gallery: {OUT} ({total_shots} screenshots)")


if __name__ == "__main__":
    main()
