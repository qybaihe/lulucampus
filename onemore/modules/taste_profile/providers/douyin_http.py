"""HTTP Douyin collector for public posts + recent likes + collects (no Playwright).

Uses operator cookies from a local JSON export. Enough for ~30 recent likes /
collects / posts before Argus usually kicks in — which is the intended demo budget.
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx

from onemore.core.errors import AppError

# Share-card paste often looks like:
# 「长按复制… https://v.douyin.com/6tRdrQEDajg/ 2@1.com :5pm」
# Only capture the short id; never swallow the trailing "2@1.com" junk.
SHORT_LINK_RE = re.compile(
    r"(?:https?://)?v\.douyin\.com/([A-Za-z0-9_-]{4,32})/?",
    re.I,
)
USER_PATH_RE = re.compile(r"/user/(MS4wLjAB[\w-]+)")
SEC_UID_RE = re.compile(r"(MS4wLjAB[\w-]{20,})")

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)


def extract_share_url(text: str) -> str | None:
    text = (text or "").strip()
    if not text:
        return None
    m = SHORT_LINK_RE.search(text)
    if m:
        return f"https://v.douyin.com/{m.group(1)}/"
    um = USER_PATH_RE.search(text)
    if um:
        return f"https://www.douyin.com/user/{um.group(1)}"
    sec = SEC_UID_RE.search(text)
    if sec and len(text) < 80:
        return f"https://www.douyin.com/user/{sec.group(1)}"
    return None


_SESSION_COOKIE_NAMES = {"sessionid", "sessionid_ss", "sid_tt", "sid_guard"}


def _pairs_from_json(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [
            f"{item['name']}={item['value']}"
            for item in raw
            if isinstance(item, dict) and item.get("name") and item.get("value") is not None
        ]
    if isinstance(raw, dict):
        if isinstance(raw.get("cookies"), list):
            return [
                f"{item['name']}={item['value']}"
                for item in raw["cookies"]
                if isinstance(item, dict) and item.get("name")
            ]
        return [f"{k}={v}" for k, v in raw.items() if isinstance(v, str)]
    raise AppError("DOUYIN_COOKIE_INVALID", "Cookie JSON 格式不正确", 503)


def _require_session_cookie(header: str) -> str:
    names = {part.split("=", 1)[0].strip() for part in header.split(";") if "=" in part}
    if not names & _SESSION_COOKIE_NAMES:
        raise AppError("DOUYIN_COOKIE_INVALID", "Cookie 缺少登录态字段（sessionid/sid_tt）", 503)
    return header


def validate_cookie_header(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        raise AppError("DOUYIN_COOKIE_MISSING", "未配置抖音运营 Cookie", 503)
    if text[0] in "{[":
        try:
            pairs = _pairs_from_json(json.loads(text))
        except json.JSONDecodeError as exc:
            raise AppError("DOUYIN_COOKIE_INVALID", "Cookie JSON 无法解析", 503) from exc
        if not pairs:
            raise AppError("DOUYIN_COOKIE_INVALID", "Cookie 为空", 503)
        return _require_session_cookie("; ".join(pairs))
    return _require_session_cookie(text)


def load_cookie_header(cookie_path: Path) -> str:
    if not cookie_path.is_file():
        raise AppError(
            "DOUYIN_COOKIE_MISSING",
            f"未找到本机抖音 Cookie 文件：{cookie_path}",
            503,
        )
    return validate_cookie_header(cookie_path.read_text("utf-8"))


def resolve_operator_cookie() -> str:
    """Load operator Cookie from env (header / B64) or the local JSON file."""
    from onemore.core.config import get_settings

    settings = get_settings()
    b64 = (settings.douyin_http_cookie_b64 or "").strip()
    raw = (settings.douyin_http_cookie or "").strip()
    if b64:
        try:
            raw = base64.b64decode(b64).decode("utf-8").strip()
        except Exception as exc:
            raise AppError("DOUYIN_COOKIE_INVALID", "DOUYIN_HTTP_COOKIE_B64 无法解码", 503) from exc
    if raw:
        return validate_cookie_header(raw)
    path = Path(settings.douyin_http_cookie_path)
    if path.is_file():
        return load_cookie_header(path)
    raise AppError(
        "DOUYIN_COOKIE_MISSING",
        "服务器未配置抖音运营 Cookie。请设置 ONEMORE_DOUYIN_HTTP_COOKIE_B64",
        503,
    )


def http_cookie_ready() -> bool:
    try:
        resolve_operator_cookie()
        return True
    except AppError:
        return False


class DouyinHttpCollector:
    def __init__(
        self,
        *,
        cookie_header: str | None = None,
        cookie_path: Path | None = None,
        timeout_seconds: float = 25.0,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        if cookie_header:
            self.cookie_header = validate_cookie_header(cookie_header)
        elif cookie_path is not None:
            self.cookie_header = load_cookie_header(cookie_path)
        else:
            self.cookie_header = resolve_operator_cookie()
        self.timeout = timeout_seconds
        self.user_agent = user_agent

    def _client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json, text/plain, */*",
                "Cookie": self.cookie_header,
            },
        )

    def resolve_sec_uid(self, share_text: str) -> dict[str, str]:
        url = extract_share_url(share_text)
        if not url:
            raise AppError(
                "DOUYIN_SHARE_URL_INVALID",
                "请粘贴抖音个人主页分享链接（v.douyin.com/...）",
                400,
            )
        # Already a user URL
        um = USER_PATH_RE.search(url)
        if um and "v.douyin.com" not in url:
            return {"sec_uid": um.group(1), "profile_url": url, "resolved_url": url}

        with self._client() as client:
            resp = client.get(
                url,
                headers={"Referer": "https://www.douyin.com/", "Accept": "text/html,*/*"},
            )
            final = str(resp.url)
            um = USER_PATH_RE.search(final)
            if um:
                sec = um.group(1)
                return {
                    "sec_uid": sec,
                    "profile_url": f"https://www.douyin.com/user/{sec}",
                    "resolved_url": final,
                }
            # HTML / redirect body fallback
            body = resp.text or ""
            m = USER_PATH_RE.search(body) or SEC_UID_RE.search(body)
            if m:
                sec = m.group(1) if m.lastindex else m.group(0)
                if not str(sec).startswith("MS4wLjAB"):
                    sec = m.group(0)
                if str(sec).startswith("MS4wLjAB"):
                    return {
                        "sec_uid": str(sec),
                        "profile_url": f"https://www.douyin.com/user/{sec}",
                        "resolved_url": final,
                    }
        raise AppError(
            "DOUYIN_PROFILE_RESOLVE_FAILED",
            "无法从分享链接解析到个人主页，请确认链接有效且喜欢列表已公开",
            422,
        )

    def _fetch_aweme_pages(
        self,
        *,
        api_path: str,
        sec_uid: str,
        referer: str,
        limit: int,
        cursor_key: str = "max_cursor",
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if limit <= 0:
            return [], {"pages": 0, "stopped": "limit_zero"}

        items: dict[str, dict[str, Any]] = {}
        cursor: Any = 0
        pages = 0
        stopped = "complete"
        meta: dict[str, Any] = {}

        with self._client() as client:
            while len(items) < limit and pages < 8:
                count = min(18, limit - len(items))
                params = {
                    "device_platform": "webapp",
                    "aid": "6383",
                    "channel": "channel_pc_web",
                    "sec_user_id": sec_uid,
                    "max_cursor": str(cursor),
                    "min_cursor": "0",
                    "count": str(count),
                    "publish_video_strategy_type": "2",
                    "version_code": "170400",
                    "version_name": "17.4.0",
                    "cookie_enabled": "true",
                    "platform": "PC",
                }
                url = f"https://www.douyin.com{api_path}?{urlencode(params)}"
                resp = client.get(url, headers={"Referer": referer})
                pages += 1
                if resp.status_code == 403 or "ArgusSecurityPlugin" in resp.text:
                    stopped = "blocked"
                    meta["http_status"] = resp.status_code
                    meta["block_body"] = resp.text[:120]
                    break
                if resp.status_code != 200:
                    stopped = "http_error"
                    meta["http_status"] = resp.status_code
                    break
                try:
                    data = resp.json()
                except Exception:
                    stopped = "bad_json"
                    break
                if data.get("status_code") not in (0, None):
                    stopped = f"status_{data.get('status_code')}"
                    meta["api_status"] = data.get("status_code")
                    break
                batch = data.get("aweme_list") or []
                for raw in batch:
                    aid = str(raw.get("aweme_id") or "")
                    if aid and aid not in items:
                        items[aid] = raw
                has_more = data.get("has_more")
                cursor = data.get(cursor_key) or data.get("cursor") or cursor
                if has_more in (0, False) or not batch:
                    stopped = "end"
                    break
                if len(items) >= limit:
                    stopped = "limit"
                    break

        return list(items.values())[:limit], {
            "pages": pages,
            "stopped": stopped,
            "returned": min(len(items), limit),
            **meta,
        }

    def _fetch_collection_pages(
        self,
        *,
        sec_uid: str,
        referer: str,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if limit <= 0:
            return [], {"pages": 0, "stopped": "limit_zero", "returned": 0}

        items: dict[str, dict[str, Any]] = {}
        cursor: Any = 0
        pages = 0
        stopped = "complete"
        meta: dict[str, Any] = {}
        query = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "sec_user_id": sec_uid,
            "publish_video_strategy_type": "2",
            "version_code": "170400",
            "version_name": "17.4.0",
            "cookie_enabled": "true",
            "platform": "PC",
        }

        with self._client() as client:
            while len(items) < limit and pages < 8:
                count = min(18, limit - len(items))
                url = (
                    "https://www.douyin.com/aweme/v1/web/aweme/listcollection/"
                    f"?{urlencode(query)}"
                )
                body = urlencode(
                    {
                        "count": str(count),
                        "cursor": str(cursor),
                        "sec_user_id": sec_uid,
                    }
                )
                resp = client.post(
                    url,
                    content=body,
                    headers={
                        "Referer": referer,
                        "Origin": "https://www.douyin.com",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                pages += 1
                if resp.status_code == 403 or "ArgusSecurityPlugin" in resp.text:
                    stopped = "blocked"
                    meta["http_status"] = resp.status_code
                    break
                if resp.status_code != 200:
                    stopped = "http_error"
                    meta["http_status"] = resp.status_code
                    break
                try:
                    data = resp.json()
                except Exception:
                    stopped = "bad_json"
                    break
                status_code = data.get("status_code")
                if status_code == 3002279:
                    stopped = "private"
                    meta["api_status"] = status_code
                    break
                if status_code not in (0, None):
                    stopped = f"status_{status_code}"
                    meta["api_status"] = status_code
                    break
                batch = data.get("aweme_list") or []
                for raw in batch:
                    aid = str(raw.get("aweme_id") or "")
                    if aid and aid not in items:
                        items[aid] = raw
                has_more = data.get("has_more")
                cursor = data.get("cursor") or cursor
                if has_more in (0, False) or not batch:
                    stopped = "end"
                    break
                if len(items) >= limit:
                    stopped = "limit"
                    break

        return list(items.values())[:limit], {
            "pages": pages,
            "stopped": stopped,
            "returned": min(len(items), limit),
            **meta,
        }

    def collect_recent(
        self,
        share_text: str,
        *,
        likes_limit: int = 30,
        posts_limit: int = 20,
        collects_limit: int = 30,
    ) -> dict[str, Any]:
        resolved = self.resolve_sec_uid(share_text)
        sec_uid = resolved["sec_uid"]
        profile_url = resolved["profile_url"]
        like_referer = f"{profile_url}?showTab=like"
        collect_referer = f"{profile_url}?showTab=favorite_collection"

        posts_raw, posts_meta = self._fetch_aweme_pages(
            api_path="/aweme/v1/web/aweme/post/",
            sec_uid=sec_uid,
            referer=profile_url,
            limit=posts_limit,
        )
        likes_raw, likes_meta = self._fetch_aweme_pages(
            api_path="/aweme/v1/web/aweme/favorite/",
            sec_uid=sec_uid,
            referer=like_referer,
            limit=likes_limit,
        )
        collects_raw, collects_meta = self._fetch_collection_pages(
            sec_uid=sec_uid,
            referer=collect_referer,
            limit=collects_limit,
        )

        if not posts_raw and not likes_raw and not collects_raw:
            raise AppError(
                "DOUYIN_HTTP_EMPTY",
                "未拉到作品、喜欢或收藏。请把主页「喜欢」和「收藏里的视频」设为公开后再试",
                422,
            )

        author = {}
        for raw in posts_raw + likes_raw + collects_raw:
            author = raw.get("author") or {}
            if author.get("nickname") or author.get("unique_id"):
                break

        avatar_url = _avatar_url(author)
        return {
            "sec_uid": sec_uid,
            "profile_url": profile_url,
            "resolved_url": resolved.get("resolved_url") or profile_url,
            "source_profile": {
                "nickname": str(author.get("nickname") or "") or None,
                "avatar_url": _avatar_as_data_url(avatar_url) or avatar_url,
                "uid": str(author.get("uid") or author.get("unique_id") or "") or None,
                "sec_uid": sec_uid,
            },
            "posts_raw": posts_raw,
            "likes_raw": likes_raw,
            "collects_raw": collects_raw,
            "meta": {
                "posts": posts_meta,
                "likes": likes_meta,
                "collects": collects_meta,
                "host": urlparse(profile_url).netloc,
            },
        }


def _avatar_url(author: dict[str, Any]) -> str | None:
    for key in ("avatar_thumb", "avatar_medium", "avatar_larger"):
        blob = author.get(key) or {}
        urls = blob.get("url_list") if isinstance(blob, dict) else None
        if isinstance(urls, list) and urls:
            return str(urls[0])
    return None


def _avatar_as_data_url(url: str | None) -> str | None:
    """Inline avatar for share-card export (avoids Douyin CDN CORS taint)."""
    if not url:
        return None
    try:
        with httpx.Client(timeout=12.0, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={
                    "User-Agent": DEFAULT_UA,
                    "Referer": "https://www.douyin.com/",
                    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                },
            )
        if resp.status_code != 200 or not resp.content:
            return None
        ctype = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
        if not ctype.startswith("image/"):
            ctype = "image/jpeg"
        return f"data:{ctype};base64,{base64.b64encode(resp.content).decode('ascii')}"
    except Exception:
        return None
