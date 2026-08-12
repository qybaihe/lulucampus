"""Server-rendered, identity-free landing page for gap share links.

缺口卡是全民可传播的社交符号：桌与座、还差一个。页面只呈现事实
（类型/时间/校区/缺口数/一句话心情），永不出现身份、名单或报名明细。
"""

from __future__ import annotations

import html
from datetime import datetime
from zoneinfo import ZoneInfo

from onemore.core.time import ensure_utc

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _slot_text(start_at: datetime | None, end_at: datetime | None) -> str:
    if start_at is None:
        return "时间待定"
    local = ensure_utc(start_at).astimezone(_SHANGHAI)
    text = f"{local.month} 月 {local.day} 日 {_WEEKDAYS[local.weekday()]} {local:%H:%M}"
    if end_at is not None:
        text += f" – {ensure_utc(end_at).astimezone(_SHANGHAI):%H:%M}"
    return text


def _seats_markup(target_size: int, missing_count: int) -> str:
    seats = []
    filled = max(target_size - missing_count, 0)
    for index in range(min(target_size, 8)):
        state = "filled" if index < filled else "empty"
        seats.append(f'<span class="seat {state}"></span>')
    return "".join(seats)


def render_share_page(view: dict) -> str:
    title = html.escape(view.get("title") or "一起上桌")
    gathering_type = html.escape(view.get("gathering_type") or "")
    campus = html.escape(view.get("campus") or "")
    mood_note = html.escape(view.get("mood_note") or "")
    slot = html.escape(_slot_text(view.get("start_at"), view.get("end_at")))
    missing = int(view.get("missing_count") or 0)
    target = int(view.get("target_size") or 0)
    joinable = bool(view.get("joinable"))
    deep_link = html.escape(view.get("deep_link") or "")
    seats = _seats_markup(target, missing)
    looking = [html.escape(str(item)) for item in (view.get("looking_for") or []) if item]
    looking_block = (
        f'<p class="looking">这桌还缺：{" · ".join(looking)}</p>' if looking else ""
    )

    if joinable and missing > 0:
        gap_text = f"还差 {missing} 人"
        state_line = "座位还空着，就等你了"
    elif joinable:
        gap_text = "即将满座"
        state_line = "手快有，手慢无"
    else:
        gap_text = "本局已收档"
        state_line = "这一桌已经开局，去看看别的局"

    og_description = f"{slot} · {campus or '校内'} · {gap_text}"
    mood_block = f'<p class="mood">“{mood_note}”</p>' if mood_note else ""
    cta_block = (
        f'<a class="cta" href="{deep_link}">上桌补位</a>'
        if joinable
        else '<span class="cta disabled">招募已结束</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {gap_text} · 噜噜成局</title>
<meta property="og:title" content="{title} · {gap_text}">
<meta property="og:description" content="{og_description}">
<meta property="og:type" content="website">
<style>
  /* 与 iOS 端 OMTheme 对齐的噜噜暖纸体系：paper/ink/yolk/card。 */
  :root {{
    --paper: #f6f4ec; --card: #fffdf8; --ink: #1f2d25; --yolk: #f6c945;
    --dim: rgba(31,45,37,0.58); --line: rgba(31,45,37,0.14);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background:
      radial-gradient(90% 60% at 50% 0%, rgba(246,201,69,0.18), transparent 60%),
      var(--paper);
    color: var(--ink); font-family: -apple-system, "PingFang SC", "Noto Sans SC", sans-serif;
    padding: 24px;
  }}
  .card {{
    width: min(420px, 100%); border: 1.5px solid var(--line); border-radius: 28px;
    background: var(--card); padding: 36px 28px 28px;
    text-align: center; box-shadow: 0 18px 44px rgba(31,45,37,0.12);
  }}
  .brand {{ font-size: 12px; letter-spacing: 0.4em; color: var(--dim); font-weight: 600; }}
  .table {{
    width: 128px; height: 128px; margin: 26px auto 8px; border-radius: 50%;
    border: 2px solid var(--ink); position: relative;
    background: radial-gradient(circle at 50% 32%, rgba(246,201,69,0.35), transparent 72%);
  }}
  .table::after {{
    content: ""; position: absolute; inset: 26px; border-radius: 50%;
    border: 1.5px dashed rgba(31,45,37,0.28);
  }}
  .seats {{ display: flex; gap: 10px; justify-content: center; margin: 18px 0 6px; }}
  .seat {{ width: 14px; height: 14px; border-radius: 50%; display: inline-block; }}
  .seat.filled {{ background: var(--ink); }}
  .seat.empty {{
    border: 2px dashed #d9a514; background: rgba(246,201,69,0.25);
    animation: pulse 1.6s ease-in-out infinite;
  }}
  @keyframes pulse {{ 50% {{ transform: scale(1.25); opacity: 0.55; }} }}
  .gap {{
    display: inline-block; margin-top: 12px; padding: 6px 18px; border-radius: 999px;
    background: var(--yolk); color: var(--ink); font-size: 26px; font-weight: 800;
    box-shadow: 0 6px 16px rgba(246,201,69,0.45);
  }}
  h1 {{ font-size: 20px; font-weight: 700; margin-top: 16px; }}
  .meta {{ margin-top: 10px; color: var(--dim); font-size: 14px; line-height: 1.7; }}
  .mood {{
    margin-top: 14px; font-size: 14px; color: var(--ink);
    border-left: 3px solid var(--yolk); padding-left: 10px; text-align: left;
    display: inline-block;
  }}
  .looking {{ margin-top: 12px; font-size: 13px; color: var(--dim); }}
  .state {{ margin-top: 18px; font-size: 13px; color: var(--dim); }}
  .cta {{
    display: block; margin-top: 18px; padding: 14px 0; border-radius: 16px;
    background: var(--ink); color: var(--card); font-weight: 700; text-decoration: none;
    font-size: 16px;
  }}
  .cta.disabled {{ background: var(--line); color: var(--dim); }}
  .foot {{ margin-top: 16px; font-size: 11px; color: var(--dim); letter-spacing: 0.2em; }}
</style>
</head>
<body>
  <main class="card">
    <div class="brand">噜噜成局 · 差一个</div>
    <div class="table" role="img" aria-label="一桌人，{gap_text}"></div>
    <div class="seats">{seats}</div>
    <div class="gap">{gap_text}</div>
    <h1>{gathering_type}{('·' + title) if title and title != gathering_type else ''}</h1>
    <p class="meta">{slot}<br>{campus or '校内'}</p>
    {mood_block}
    {looking_block}
    <p class="state">{state_line}</p>
    {cta_block}
    <div class="foot">匿名招募 · 满座即成局 · 失败无痕</div>
  </main>
</body>
</html>"""
