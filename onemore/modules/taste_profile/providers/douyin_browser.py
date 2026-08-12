"""Real Douyin browser provider based on the validated Playwright path.

Verified reference run: 153 favorite API pages / 2,383 unique likes, final
page has_more=0. We reuse response interception of ``/aweme/v1/web/aweme/favorite/``
as the authoritative source and never mix DOM-only recommendation links into
the like list. Cookies live only inside the per-import Chrome profile directory
under the task runtime root and are deleted on cleanup.
"""

from __future__ import annotations

import base64
import io
import json
import re
import shutil
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import suppress
from pathlib import Path
from typing import Any

from onemore.core.config import Settings
from onemore.modules.taste_profile.analyzer import normalize_item
from onemore.modules.taste_profile.providers.base import (
    DouyinProvider,
    PageResult,
    ProviderError,
    QRResult,
)

LOGIN_COOKIE_FLAGS = {"sessionid", "sessionid_ss", "sid_tt", "sid_guard"}
QR_SCANNED_STATUSES = {"2", "scanned", "scan"}
QR_CONFIRMED_STATUSES = {"3", "confirmed", "success"}
FAVORITE_API_MARKER = "/aweme/v1/web/aweme/favorite/"
USER_URL_PATTERN = re.compile(r"/user/([\w-]+)")
SEC_UID_PATTERN = re.compile(r"MS4wLjAB[\w-]+")
STABLE_ROUND_FALLBACK = 8
SCROLL_WAIT_SECONDS = 0.9
QR_PREPARE_TIMEOUT_SECONDS = 30
USER_RESPONSE_MARKERS = (
    "/user/self",
    "/user/profile",
    "/user/detail",
    "/account/info",
    "/aweme/v1/web/user/",
)
# Prefer network-intercepted QR payload; DOM is a fallback for new-device friction.
LOGIN_ENTRY_URLS = (
    "https://www.douyin.com/",
    "https://www.douyin.com/?recommend=1",
    "https://www.douyin.com/discover",
)

LOGIN_MODAL_TRIGGERS = (
    'button:has-text("登录")',
    'div[class*="login"]:has-text("登录")',
    'a:has-text("登录")',
    'span:has-text("登录")',
    'p:has-text("登录")',
    'div[data-e2e="login-button"]',
)

QR_CANDIDATE_SELECTORS = (
    'img[class*="qrcode"]',
    'img[class*="qr-code"]',
    'img[src*="qrcode"]',
    'img[src*="qr_code"]',
    'div[class*="qr-code"] img',
    'div[class*="qrcode"] img',
    'div[class*="web-login-modal"] img',
    'div[class*="login-modal"] img',
    'div[class*="login"] canvas',
    'canvas',
)

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
"""


class DouyinBrowserProvider(DouyinProvider):
    """Drives an isolated persistent Chrome context for one import task."""

    def __init__(self, import_id: str, runtime_dir: Path, settings: Settings) -> None:
        super().__init__(import_id, runtime_dir, settings)
        self.profile_url: str | None = None
        self._cancelled = threading.Event()
        self._pw: Any = None
        self._context: Any = None
        self._page: Any = None
        self._sec_uid: str | None = None
        self._response_buffer: list[dict[str, Any]] = []
        self._user_payloads: list[dict[str, Any]] = []
        self._qr_url: str | None = None
        self._qr_status: str | None = None
        self._qr_redirect_url: str | None = None
        self._redirect_followed = False
        self._profile_dir = runtime_dir / "chrome-profile"

    # ------------------------------------------------------------------ #
    # lifecycle
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        executable = Path(self.settings.douyin_browser_executable)
        if not executable.is_file():
            raise ProviderError(
                "DOUYIN_BROWSER_UNAVAILABLE",
                f"未找到浏览器：{self.settings.douyin_browser_executable}",
            )
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        # Fresh Chrome profile each import avoids stale device trust / half-login
        # state that often breaks QR scanning on a "new" headless environment.
        shutil.rmtree(self._profile_dir, ignore_errors=True)
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        try:
            from playwright.sync_api import sync_playwright

            self._pw = sync_playwright().start()
            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=str(self._profile_dir),
                headless=self.settings.douyin_browser_headless,
                executable_path=str(executable),
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=Translate,IsolateOrigins,site-per-process",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                    "--lang=zh-CN",
                ],
                viewport={"width": 1440, "height": 960},
                locale="zh-CN",
                timezone_id="Asia/Shanghai",
                ignore_default_args=["--enable-automation"],
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
            self._context.add_init_script(STEALTH_INIT_SCRIPT)
        except Exception as exc:
            self.cleanup()
            raise ProviderError(
                "DOUYIN_BROWSER_UNAVAILABLE",
                "无法启动浏览器会话，请检查 Playwright 与 Chrome 安装",
            ) from exc
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.on("response", self._capture_login_response)

    def prepare_qr(self, version: int) -> QRResult:
        self._ensure_page()
        self._qr_url = None
        self._qr_status = None
        self._qr_redirect_url = None
        self._redirect_followed = False
        image = None
        last_error: Exception | None = None
        for entry_url in LOGIN_ENTRY_URLS:
            try:
                self._page.goto(entry_url, wait_until="domcontentloaded", timeout=45000)
                self._page.wait_for_timeout(2500)
                image = self._wait_for_qr_image(timeout_seconds=QR_PREPARE_TIMEOUT_SECONDS)
                if image:
                    break
            except Exception as exc:  # noqa: BLE001 — try next entry URL
                last_error = exc
                continue
        if image is None:
            detail = f"：{last_error}" if last_error else ""
            raise ProviderError(
                "DOUYIN_QR_NOT_FOUND",
                f"登录页未找到二维码，请重试{detail}",
            )
        return QRResult(
            image_data_url=f"data:image/png;base64,{image}",
            expires_in_seconds=self.settings.douyin_qr_timeout_seconds,
        )

    def _wait_for_qr_image(self, *, timeout_seconds: float) -> str | None:
        deadline = time.monotonic() + timeout_seconds
        last_open_attempt = 0.0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now - last_open_attempt >= 1.2:
                self._open_login_modal()
                self._switch_to_qr_tab()
                last_open_attempt = now
            # Prefer network-captured QR token; DOM screenshots are often
            # unreadable after device-risk / captcha UI shifts.
            if self._qr_url:
                with suppress(Exception):
                    return self._qr_url_data(self._qr_url)
            image = self._capture_qr_image()
            if image is not None:
                return image
            self._page.wait_for_timeout(300)
        return None

    def _switch_to_qr_tab(self) -> None:
        """Some Douyin builds default to SMS login on new devices."""
        for label in ("扫码登录", "二维码登录", "扫码"):
            with suppress(Exception):
                tab = self._page.get_by_text(label, exact=False).first
                if tab.count() and tab.is_visible():
                    tab.click(timeout=2000)
                    self._page.wait_for_timeout(400)
                    return

    def is_logged_in(self) -> bool:
        if self._context is None:
            return False
        if self._qr_redirect_url and not self._redirect_followed:
            self._redirect_followed = True
            with suppress(Exception):
                self._page.goto(
                    self._qr_redirect_url,
                    wait_until="domcontentloaded",
                    timeout=45000,
                )
                self._page.wait_for_timeout(1200)
        try:
            cookies = self._context.cookies(
                ["https://www.douyin.com", "https://www.iesdouyin.com"]
            )
        except Exception:
            return False
        names = {cookie.get("name") for cookie in cookies}
        return bool(names & LOGIN_COOKIE_FLAGS)

    def is_qr_scanned(self) -> bool:
        return self._qr_status in QR_SCANNED_STATUSES | QR_CONFIRMED_STATUSES

    def is_phone_verification_required(self) -> bool:
        if self._qr_status not in QR_CONFIRMED_STATUSES:
            return False
        with suppress(Exception):
            phone_input = self._page.locator('input[placeholder="请输入手机号"]:visible')
            if phone_input.count():
                return True
            text = self._page.locator("body").inner_text()
            return "验证手机号" in text or "手机号验证" in text
        return False

    def request_sms_code(self, phone: str, country_code: str) -> None:
        self._ensure_page()
        self._open_login_modal()
        with suppress(Exception):
            tab = self._page.get_by_text("验证码登录", exact=True).last
            if tab.is_visible():
                tab.click(timeout=3000)
        self._page.wait_for_timeout(400)
        phone_input = self._page.locator('input[placeholder="请输入手机号"]:visible').last
        if not phone_input.count():
            raise ProviderError("DOUYIN_PHONE_LOGIN_UNAVAILABLE", "未找到手机号登录入口")
        self._fill_country_code(country_code)
        phone_input.fill(phone)
        trigger = self._page.get_by_text("获取验证码", exact=True).last
        if not trigger.count() or not trigger.is_visible():
            raise ProviderError("DOUYIN_PHONE_LOGIN_UNAVAILABLE", "未找到获取验证码按钮")
        trigger.click(timeout=5000)
        self._page.wait_for_timeout(900)
        error = self._phone_login_error()
        if error:
            raise ProviderError("DOUYIN_SMS_SEND_FAILED", error)

    def submit_sms_code(self, code: str) -> None:
        self._ensure_page()
        code_input = self._page.locator('input[placeholder="请输入验证码"]:visible').last
        if not code_input.count():
            raise ProviderError("DOUYIN_SMS_NOT_REQUESTED", "请先获取短信验证码")
        code_input.fill(code)
        login = self._page.get_by_text("登录", exact=True).last
        if not login.count() or not login.is_visible():
            raise ProviderError("DOUYIN_PHONE_LOGIN_UNAVAILABLE", "未找到手机号登录按钮")
        login.click(timeout=5000)
        self._page.wait_for_timeout(1000)
        error = self._phone_login_error()
        if error:
            raise ProviderError("DOUYIN_SMS_CODE_INVALID", error)

    def resolve_profile(self) -> dict[str, Any]:
        self._ensure_page()
        with suppress(Exception):
            self._page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=45000)
            self._page.wait_for_timeout(2500)
        deadline = time.monotonic() + 15
        sec_uid = None
        while time.monotonic() < deadline and not sec_uid:
            sec_uid = (
                self._sec_uid_from_storage()
                or self._sec_uid_from_avatar()
                or self._sec_uid_from_user_payloads()
                or self._sec_uid_from_page_state()
                or self._sec_uid_from_profile_url()
            )
            if not sec_uid:
                self._page.wait_for_timeout(500)
        if not sec_uid:
            raise ProviderError("DOUYIN_PROFILE_NOT_FOUND", "登录后仍无法识别当前账号")
        self._sec_uid = sec_uid
        meta = self._user_meta()
        meta["sec_uid"] = sec_uid
        return meta

    def collect(
        self,
        max_items: int,
        is_cancelled: Callable[[], bool],
    ) -> Iterator[PageResult]:
        if not self._sec_uid:
            raise ProviderError("DOUYIN_PROFILE_NOT_FOUND", "缺少当前账号 sec_uid")
        self._start_collection()
        unique: dict[str, dict[str, Any]] = {}
        api_pages = 0
        stable = 0
        deadline = time.monotonic() + self.settings.douyin_collection_timeout_seconds
        while time.monotonic() < deadline:
            if is_cancelled():
                break
            drained = False
            while self._response_buffer:
                data = self._response_buffer.pop(0)
                raw_items = data.get("aweme_list") or []
                more = data.get("has_more") not in (0, False)
                new_items: list[dict[str, Any]] = []
                for raw in raw_items:
                    aweme_id = str(raw.get("aweme_id") or "")
                    if not aweme_id or aweme_id in unique:
                        continue
                    unique[aweme_id] = raw
                    new_items.append(normalize_item(raw))
                api_pages += 1
                drained = True
                yield PageResult(
                    page_index=api_pages,
                    items=new_items,
                    api_pages=api_pages,
                    items_collected=len(unique),
                    has_more=more,
                )
                if not more or (max_items and len(unique) >= max_items):
                    return
            stable = 0 if drained else stable + 1
            if stable >= STABLE_ROUND_FALLBACK:
                raise ProviderError(
                    "DOUYIN_COLLECTION_STALLED",
                    "喜欢列表多轮滚动没有新增数据，且尚未到达末页",
                )
            self._scroll_once()
            self._page.wait_for_timeout(int(SCROLL_WAIT_SECONDS * 1000))
        raise ProviderError("DOUYIN_COLLECTION_TIMEOUT", "采集喜欢内容超过总时限")

    def cancel(self) -> None:
        self._cancelled.set()

    def cleanup(self) -> None:
        self._cancelled.set()
        if self._context is not None:
            with suppress(Exception):
                self._context.close()
            self._context = None
        if self._pw is not None:
            with suppress(Exception):
                self._pw.stop()
            self._pw = None
        shutil.rmtree(self._profile_dir, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # private helpers
    # ------------------------------------------------------------------ #
    def _ensure_page(self) -> None:
        if self._page is None or self._context is None:
            raise ProviderError("DOUYIN_BROWSER_UNAVAILABLE", "浏览器会话尚未就绪")

    def _open_login_modal(self) -> None:
        with suppress(Exception):
            target = self._page.get_by_role("button", name="登录", exact=True).first
            if target.count() and target.is_visible():
                target.click(timeout=2500)
                return
        for selector in LOGIN_MODAL_TRIGGERS:
            try:
                target = self._page.locator(selector).first
                if target.count() and target.is_visible():
                    target.click(timeout=2500)
                    return
            except Exception:
                continue
        for candidate in QR_CANDIDATE_SELECTORS:
            with suppress(Exception):
                if self._page.locator(candidate).count():
                    return

    def _fill_country_code(self, country_code: str) -> None:
        area = self._page.locator('input[name="web-login-area-code-input"]:visible').last
        if not area.count():
            return
        with suppress(Exception):
            current = area.input_value().lstrip("+")
            if current == country_code:
                return
        normalized = f"+{country_code}"
        with suppress(Exception):
            area.fill(normalized)
            area.press("Enter")

    def _phone_login_error(self) -> str | None:
        with suppress(Exception):
            text = self._page.locator("body").inner_text()
            for message in (
                "请输入正确的手机号",
                "验证码错误",
                "验证码已过期",
                "发送过于频繁",
                "请完成验证",
                "操作频繁",
            ):
                if message in text:
                    return message
        return None

    def _capture_qr_image(self) -> str | None:
        candidates: list[tuple[int, Any]] = []
        for frame in self._page.frames:
            for selector in QR_CANDIDATE_SELECTORS:
                locator = frame.locator(selector)
                with suppress(Exception):
                    for index in range(min(locator.count(), 8)):
                        element = locator.nth(index)
                        box = element.bounding_box()
                        if not box or not element.is_visible():
                            continue
                        width = float(box["width"])
                        height = float(box["height"])
                        if min(width, height) < 110 or max(width, height) > 520:
                            continue
                        if abs(width - height) > max(width, height) * 0.3:
                            continue
                        hint = " ".join(
                            filter(
                                None,
                                (
                                    element.get_attribute("class"),
                                    element.get_attribute("src"),
                                    selector,
                                ),
                            )
                        ).lower()
                        score = 100 if "qr" in hint else 0
                        score -= int(abs(width - 220))
                        candidates.append((score, element))
        for _, element in sorted(candidates, key=lambda item: item[0], reverse=True):
            with suppress(Exception):
                raw = element.screenshot(type="png")
                if raw and len(raw) > 512:
                    return base64.b64encode(raw).decode("ascii")
        return None

    def _capture_login_response(self, response) -> None:
        url = response.url
        lower = url.lower()
        is_qr_create = any(
            token in lower
            for token in (
                "get_qrcode",
                "getqrcode",
                "qrcode/get",
                "sso/get_qrcode",
                "passport/web/get_qrcode",
            )
        )
        is_qr_check = any(
            token in lower
            for token in (
                "check_qrconnect",
                "checkqrconnect",
                "qrcode/check",
                "sso/check_qrconnect",
                "passport/web/check_qrconnect",
            )
        )
        if not is_qr_create and not is_qr_check and not any(
            marker in url for marker in USER_RESPONSE_MARKERS
        ):
            return
        try:
            data = response.json()
        except Exception:
            return
        if not isinstance(data, dict):
            return
        if is_qr_create:
            qr_url = self._find_string(
                data,
                {
                    "qrcode_index_url",
                    "qrcode_url",
                    "qr_url",
                    "qrcode_index",
                    "token_url",
                },
            )
            if qr_url:
                self._qr_url = qr_url
            # Some endpoints return a bare token that must be encoded locally.
            token = self._find_string(data, {"token", "qrcode", "qrcode_token"})
            if not self._qr_url and token and token.startswith("http"):
                self._qr_url = token
        elif is_qr_check:
            payload = data.get("data")
            if isinstance(payload, dict):
                status = payload.get("status")
                if status is None:
                    status = payload.get("qrcode_status") or payload.get("status_code")
                self._qr_status = str(status) if status is not None else None
                redirect_url = payload.get("redirect_url") or payload.get("redirect_url_list")
                if isinstance(redirect_url, list) and redirect_url:
                    redirect_url = redirect_url[0]
                if self._qr_status in QR_CONFIRMED_STATUSES and isinstance(
                    redirect_url, str
                ):
                    self._qr_redirect_url = redirect_url
        else:
            self._user_payloads.append(data)

    @staticmethod
    def _qr_url_data(url: str) -> str:
        import qrcode

        buffer = io.BytesIO()
        qrcode.make(url).save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    def _start_collection(self) -> None:
        self._ensure_page()
        self._response_buffer = []

        def on_response(response) -> None:
            if FAVORITE_API_MARKER not in response.url:
                return
            try:
                data = response.json()
            except Exception:
                return
            if isinstance(data, dict):
                self._response_buffer.append(data)

        self._page.on("response", on_response)
        url = f"https://www.douyin.com/user/{self._sec_uid}?showTab=like"
        self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
        self._page.wait_for_timeout(3000)
        try:
            self._page.get_by_text("喜欢", exact=True).first.click(timeout=3000)
            self._page.wait_for_timeout(1800)
        except Exception:
            pass

    def _scroll_once(self) -> None:
        try:
            self._page.evaluate(
                """() => {
                  const els = Array.from(document.querySelectorAll('*'))
                    .filter(e => e.scrollHeight > e.clientHeight + 200);
                  els.sort((a, b) => b.scrollHeight - a.scrollHeight);
                  const el = els[0];
                  if (!el) return;
                  el.scrollTop = el.scrollHeight;
                }"""
            )
            self._page.mouse.wheel(0, 5000)
        except Exception:
            pass

    def _sec_uid_from_page_state(self) -> str | None:
        try:
            state = self._page.evaluate(
                "() => window.__INITIAL_STATE__ || window.RENDER_DATA || null"
            )
        except Exception:
            return None
        if isinstance(state, str):
            try:
                state = json.loads(state)
            except Exception:
                return None
        return self._search_sec_uid(state)

    def _search_sec_uid(self, node: Any) -> str | None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"sec_uid", "sec_user_id", "secUid"} and isinstance(value, str):
                    match = SEC_UID_PATTERN.search(value)
                    if match:
                        return match.group(0)
                found = self._search_sec_uid(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = self._search_sec_uid(item)
                if found:
                    return found
        return None

    def _sec_uid_from_user_payloads(self) -> str | None:
        for payload in reversed(self._user_payloads):
            found = self._search_sec_uid(payload)
            if found:
                return found
        return None

    def _sec_uid_from_avatar(self) -> str | None:
        try:
            href = self._page.evaluate(
                """() => {
                  const links = Array.from(document.querySelectorAll('a[href*="/user/"]'))
                    .map(a => ({a, r: a.getBoundingClientRect()}))
                    .filter(x => x.r.width > 0 && x.r.height > 0 && x.r.top >= 0 && x.r.top < 180)
                    .sort((x, y) => y.r.left - x.r.left);
                  return links.length ? links[0].a.href : null;
                }"""
            )
        except Exception:
            return None
        if not href:
            return None
        match = USER_URL_PATTERN.search(href)
        return match.group(1) if match else None

    def _sec_uid_from_storage(self) -> str | None:
        try:
            values = self._page.evaluate(
                """() => [
                  ...Object.values(localStorage),
                  ...Object.values(sessionStorage)
                ]"""
            )
        except Exception:
            return None
        for value in values or []:
            if not isinstance(value, str):
                continue
            match = SEC_UID_PATTERN.search(value)
            if match:
                return match.group(0)
            with suppress(json.JSONDecodeError):
                found = self._search_sec_uid(json.loads(value))
                if found:
                    return found
        return None

    def _sec_uid_from_profile_url(self) -> str | None:
        if not self.profile_url:
            return None
        match = USER_URL_PATTERN.search(self.profile_url)
        return match.group(1) if match else None

    def _user_meta(self) -> dict[str, Any]:
        info: dict[str, Any] = {}
        for payload in reversed(self._user_payloads):
            info = self._find_user_info(payload) or {}
            if info:
                break
        try:
            state = self._page.evaluate("() => window.__INITIAL_STATE__ || null")
            info = info or self._find_user_info(state) or {}
        except Exception:
            pass
        return {
            "nickname": str(info.get("nickname") or ""),
            "avatar_url": info.get("avatar_url"),
            "uid": str(info.get("uid") or "") if info.get("uid") else None,
        }

    def _find_user_info(self, node: Any) -> dict[str, Any] | None:
        if isinstance(node, dict):
            candidate_sec_uid = self._search_sec_uid(node)
            if (
                isinstance(node.get("nickname"), str)
                and candidate_sec_uid == self._sec_uid
            ):
                return node
            for value in node.values():
                found = self._find_user_info(value)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = self._find_user_info(item)
                if found:
                    return found
        return None

    def _find_string(self, node: Any, keys: set[str]) -> str | None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in keys and isinstance(value, str) and value:
                    return value
                found = self._find_string(value, keys)
                if found:
                    return found
        elif isinstance(node, list):
            for item in node:
                found = self._find_string(item, keys)
                if found:
                    return found
        return None
