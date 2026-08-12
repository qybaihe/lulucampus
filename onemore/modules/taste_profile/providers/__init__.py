from __future__ import annotations

from pathlib import Path

from onemore.core.config import Settings
from onemore.modules.taste_profile.providers.base import DouyinProvider

__all__ = ["DouyinProvider", "create_provider"]


def create_provider(
    import_id: str,
    runtime_dir: Path,
    settings: Settings,
) -> DouyinProvider:
    if settings.douyin_mode == "browser":
        from onemore.modules.taste_profile.providers.douyin_browser import DouyinBrowserProvider

        return DouyinBrowserProvider(import_id, runtime_dir, settings)
    from onemore.modules.taste_profile.providers.fake import FakeDouyinProvider

    return FakeDouyinProvider(import_id, runtime_dir, settings)
