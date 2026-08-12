"""Provider contract for Douyin like-list collection.

The browser provider keeps every login artifact inside the task runtime
directory and never exposes cookie values to the API, logs or database.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from onemore.core.config import Settings


class ProviderError(Exception):
    """Stable provider failure safe to persist and return to clients."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class QRResult:
    image_data_url: str
    expires_in_seconds: int


@dataclass
class PageResult:
    page_index: int
    items: list[dict[str, Any]]
    api_pages: int
    items_collected: int
    has_more: bool


class DouyinProvider(ABC):
    """Lifecycle used by the taste import orchestrator.

    All provider methods run on a single worker thread, so a Playwright sync
    context can be created and closed inside the same thread.
    """

    def __init__(
        self,
        import_id: str,
        runtime_dir: Path,
        settings: Settings,
    ) -> None:
        self.import_id = import_id
        self.runtime_dir = runtime_dir
        self.settings = settings
        self.profile_url: str | None = None

    @abstractmethod
    def start(self) -> None:
        """Prepare the isolated runtime directory / browser session."""

    @abstractmethod
    def prepare_qr(self, version: int) -> QRResult:
        """Open the login entry and return a fresh QR snapshot."""

    @abstractmethod
    def is_logged_in(self) -> bool:
        """Return True once a login-state cookie flag is observed."""

    @abstractmethod
    def is_qr_scanned(self) -> bool:
        """Return True once the mobile app has scanned the QR code."""

    @abstractmethod
    def is_phone_verification_required(self) -> bool:
        """Return True after QR scan when Douyin requires phone verification."""

    @abstractmethod
    def request_sms_code(self, phone: str, country_code: str) -> None:
        """Request an SMS code without persisting the raw phone number."""

    @abstractmethod
    def submit_sms_code(self, code: str) -> None:
        """Submit an SMS code without persisting it."""

    @abstractmethod
    def resolve_profile(self) -> dict[str, Any]:
        """Identify the current account (nickname / uid / sec_uid)."""

    @abstractmethod
    def collect(
        self,
        max_items: int,
        is_cancelled: Callable[[], bool],
    ) -> Iterator[PageResult]:
        """Stream like items until has_more=0, the cap, a stall or timeout."""

    @abstractmethod
    def cancel(self) -> None:
        """Signal the current browser activity to stop."""

    @abstractmethod
    def cleanup(self) -> None:
        """Close the browser/context and delete isolated login state."""
