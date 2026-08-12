#!/usr/bin/env python3
"""Probe: import taste signals from a Douyin share link / unique_id using local cookies.

Does NOT log in as the target. Uses operator cookies from DouK auth/cookies.json,
opens the target profile, and compares:
  - public posts (aweme/post)
  - likes tab (aweme/favorite) — often private for others
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
COOKIES_PATH = ROOT / "douyin_like_profile/DouK-Downloader/auth/cookies.json"
OUT_DIR = ROOT / "runtime/douyin_link_probe"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SHORT_LINK_RE = re.compile(r"https?://v\.douyin\.com/[\w/-]+/?")
USER_PATH_RE = re.compile(r"/user/(MS4wLjAB[\w-]+)")
UNIQUE_ID_RE = re.compile(r"^[A-Za-z0-9._-]{2,64}$")
POST_MARKERS = ("/aweme/v1/web/aweme/post/", "/aweme/v1/web/aweme/post/?")
FAV_MARKERS = ("/aweme/v1/web/aweme/favorite/",)
SEARCH_MARKERS = (
    "/aweme/v1/web/discover/search/",
    "/aweme/v1/web/general/search/",
    "/aweme/v1/web/search/item/",
)


def load_cookies() -> list[dict]:
    raw = json.loads(COOKIES_PATH.read_text("utf-8"))
    assert isinstance(raw, list) and raw, "cookies.json empty"
    return raw


def normalize_input(text: str) -> dict[str, str | None]:
    text = text.strip()
    m = SHORT_LINK_RE.search(text)
    if m:
        return {"kind": "short_link", "value": m.group(0).rstrip("/")}
    if "douyin.com/user/" in text:
        um = USER_PATH_RE.search(text)
        return {
            "kind": "user_url",
            "value": text if text.startswith("http") else f"https://www.douyin.com{um.group(0) if um else ''}",
            "sec_uid": um.group(1) if um else None,
        }
    if UNIQUE_ID_RE.fullmatch(text):
        return {"kind": "unique_id", "value": text}
    return {"kind": "raw", "value": text}


def cookie_ok(names: set[str]) -> bool:
    return bool(names & {"sessionid", "sessionid_ss", "sid_tt", "sid_guard"})


def summarize_items(items: list[dict], limit: int = 5) -> list[dict]:
    out = []
    for raw in items[:limit]:
        author = raw.get("author") or {}
        out.append(
            {
                "aweme_id": str(raw.get("aweme_id") or ""),
                "desc": str(raw.get("desc") or "")[:80],
                "author": author.get("nickname"),
                "unique_id": author.get("unique_id") or author.get("short_id"),
            }
        )
    return out


def probe(target: str, *, max_rounds: int = 8, headed: bool = True) -> dict:
    parsed = normalize_input(target)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    profile_dir = OUT_DIR / f"chrome_{int(time.time())}"
    if profile_dir.exists():
        shutil.rmtree(profile_dir, ignore_errors=True)
    profile_dir.mkdir(parents=True, exist_ok=True)

    result: dict = {
        "input": target,
        "parsed": parsed,
        "resolved_url": None,
        "sec_uid": None,
        "source_profile": None,
        "cookie_login": False,
        "apis": {"post_pages": 0, "favorite_pages": 0, "search_hits": 0},
        "posts": {"count": 0, "has_more_last": None, "samples": []},
        "favorites": {"count": 0, "has_more_last": None, "samples": [], "private_or_empty": None},
        "errors": [],
        "notes": [],
    }

    posts: dict[str, dict] = {}
    favorites: dict[str, dict] = {}
    user_payloads: list[dict] = []

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            executable_path=CHROME,
            headless=not headed,
            locale="zh-CN",
            viewport={"width": 1280, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        try:
            context.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            context.add_cookies(load_cookies())
            page = context.new_page()

            def on_response(resp):
                url = resp.url
                try:
                    if any(m in url for m in POST_MARKERS):
                        data = resp.json()
                        result["apis"]["post_pages"] += 1
                        for item in data.get("aweme_list") or []:
                            aid = str(item.get("aweme_id") or "")
                            if aid:
                                posts[aid] = item
                        result["posts"]["has_more_last"] = data.get("has_more")
                    elif any(m in url for m in FAV_MARKERS):
                        data = resp.json()
                        result["apis"]["favorite_pages"] += 1
                        for item in data.get("aweme_list") or []:
                            aid = str(item.get("aweme_id") or "")
                            if aid:
                                favorites[aid] = item
                        result["favorites"]["has_more_last"] = data.get("has_more")
                    elif any(m in url for m in SEARCH_MARKERS):
                        data = resp.json()
                        result["apis"]["search_hits"] += 1
                        for key in ("user_list", "data", "user_info_list"):
                            blob = data.get(key)
                            if isinstance(blob, list):
                                user_payloads.extend(
                                    [x for x in blob if isinstance(x, dict)]
                                )
                    if "/user/" in url and ("detail" in url or "profile" in url or "/user/self" in url):
                        with suppress_json(resp, user_payloads):
                            pass
                except Exception:
                    return

            page.on("response", on_response)

            # Warm session / confirm cookie login
            page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            names = {c.get("name") for c in context.cookies(["https://www.douyin.com"])}
            result["cookie_login"] = cookie_ok(names)
            if not result["cookie_login"]:
                result["errors"].append("LOCAL_COOKIE_INVALID_OR_EXPIRED")
                return result

            sec_uid = None
            resolved = None

            if parsed["kind"] == "short_link":
                page.goto(parsed["value"], wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(3500)
                resolved = page.url
                um = USER_PATH_RE.search(resolved)
                if um:
                    sec_uid = um.group(1)
                else:
                    # share cards sometimes land on a video; click avatar / user link
                    with suppress_exc():
                        link = page.locator('a[href*="/user/MS4wLjAB"]').first
                        if link.count():
                            href = link.get_attribute("href") or ""
                            um = USER_PATH_RE.search(href)
                            if um:
                                sec_uid = um.group(1)
                                resolved = f"https://www.douyin.com/user/{sec_uid}"
                                page.goto(resolved, wait_until="domcontentloaded", timeout=60000)
                                page.wait_for_timeout(2500)

            elif parsed["kind"] == "user_url":
                resolved = parsed["value"]
                sec_uid = parsed.get("sec_uid")
                page.goto(resolved, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2500)

            elif parsed["kind"] == "unique_id":
                # Search people
                q = parsed["value"]
                search_url = f"https://www.douyin.com/search/{q}?type=user"
                page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(4000)
                # Prefer exact unique_id match in DOM
                with suppress_exc():
                    cards = page.locator('a[href*="/user/MS4wLjAB"]')
                    n = min(cards.count(), 12)
                    for i in range(n):
                        href = cards.nth(i).get_attribute("href") or ""
                        text = cards.nth(i).inner_text()
                        um = USER_PATH_RE.search(href)
                        if not um:
                            continue
                        if q.lower() in text.lower() or q.lower() in href.lower():
                            sec_uid = um.group(1)
                            break
                    if not sec_uid and n:
                        href = cards.first.get_attribute("href") or ""
                        um = USER_PATH_RE.search(href)
                        if um:
                            sec_uid = um.group(1)
                            result["notes"].append("unique_id_search_took_first_result")
                if sec_uid:
                    resolved = f"https://www.douyin.com/user/{sec_uid}"
                    page.goto(resolved, wait_until="domcontentloaded", timeout=60000)
                    page.wait_for_timeout(2500)

            result["resolved_url"] = resolved or page.url
            if not sec_uid:
                um = USER_PATH_RE.search(page.url)
                if um:
                    sec_uid = um.group(1)
            result["sec_uid"] = sec_uid

            if not sec_uid:
                result["errors"].append("SEC_UID_RESOLVE_FAILED")
                page.screenshot(path=str(OUT_DIR / "resolve_failed.png"), full_page=True)
                return result

            # Collect posts (works tab)
            post_url = f"https://www.douyin.com/user/{sec_uid}"
            page.goto(post_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            with suppress_exc():
                page.get_by_text("作品", exact=True).first.click(timeout=2500)
                page.wait_for_timeout(1500)
            for _ in range(max_rounds):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(900)

            # Collect likes tab if visible
            like_url = f"https://www.douyin.com/user/{sec_uid}?showTab=like"
            page.goto(like_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            with suppress_exc():
                page.get_by_text("喜欢", exact=True).first.click(timeout=2500)
                page.wait_for_timeout(1500)
            body_text = ""
            with suppress_exc():
                body_text = page.locator("body").inner_text()[:2000]
            private_hints = any(
                x in body_text
                for x in ("喜欢列表已设为私密", "私密", "暂无内容", "还没有喜欢")
            )
            for _ in range(max_rounds):
                page.mouse.wheel(0, 4000)
                page.wait_for_timeout(900)

            # Best-effort profile meta from page
            meta = {"sec_uid": sec_uid}
            with suppress_exc():
                title = page.title()
                meta["page_title"] = title
            with suppress_exc():
                nick = page.locator('h1, [data-e2e="user-info"] span').first.inner_text(
                    timeout=2000
                )
                meta["nickname_guess"] = nick.strip()[:80]
            result["source_profile"] = meta

            result["posts"]["count"] = len(posts)
            result["posts"]["samples"] = summarize_items(list(posts.values()))
            result["favorites"]["count"] = len(favorites)
            result["favorites"]["samples"] = summarize_items(list(favorites.values()))
            result["favorites"]["private_or_empty"] = (
                result["favorites"]["count"] == 0 and private_hints
            ) or (result["favorites"]["count"] == 0 and result["apis"]["favorite_pages"] == 0)

            if result["posts"]["count"] == 0 and result["favorites"]["count"] == 0:
                result["errors"].append("NO_ITEMS_COLLECTED")
                page.screenshot(path=str(OUT_DIR / "empty.png"), full_page=True)
            else:
                result["notes"].append(
                    "posts_ok" if result["posts"]["count"] else "posts_empty"
                )
                result["notes"].append(
                    "favorites_ok"
                    if result["favorites"]["count"]
                    else "favorites_unavailable_or_private"
                )
        finally:
            context.close()
            shutil.rmtree(profile_dir, ignore_errors=True)

    return result


class suppress_exc:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return True


def suppress_json(resp, bucket: list):
    try:
        data = resp.json()
        if isinstance(data, dict):
            bucket.append(data)
    except Exception:
        return


def main(argv: list[str]) -> int:
    targets = argv[1:] or [
        "yinhe18985",
        "https://v.douyin.com/72Q4_JwqJxg/",
    ]
    # Allow the long share card paste as one arg
    if len(argv) > 1 and "v.douyin.com" in " ".join(argv[1:]) and len(argv) > 2:
        joined = " ".join(argv[1:])
        targets = []
        if SHORT_LINK_RE.search(joined):
            targets.append(SHORT_LINK_RE.search(joined).group(0))
        for part in argv[1:]:
            if UNIQUE_ID_RE.fullmatch(part.strip()):
                targets.insert(0, part.strip())
        if not targets:
            targets = [joined]

    all_results = []
    for target in targets:
        print(f"\n=== PROBE {target} ===", flush=True)
        try:
            r = probe(target, headed=True, max_rounds=6)
        except Exception as exc:
            r = {"input": target, "errors": [repr(exc)]}
        all_results.append(r)
        print(json.dumps(r, ensure_ascii=False, indent=2), flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "probe_results.json"
    out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), "utf-8")
    print(f"\nWrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
