from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from onemore.core.auth import current_user
from onemore.core.config import get_settings
from onemore.core.database import get_db
from onemore.core.errors import AppError
from onemore.core.schemas import APIResponse
from onemore.db.models import User
from onemore.modules.media import service
from onemore.modules.media.schemas import ImageAssetView

router = APIRouter(prefix="/media", tags=["media"])


def _optional_positive_int(raw: str | None, name: str) -> int | None:
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise AppError("IMAGE_DIMENSION_INVALID", f"{name} 必须是整数", 422) from exc


@router.post(
    "/images",
    response_model=APIResponse[ImageAssetView],
    status_code=status.HTTP_201_CREATED,
    summary="Upload raw image bytes before sending an image message",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                media_type: {
                    "schema": {"type": "string", "format": "binary"}
                }
                for media_type in ("image/jpeg", "image/png", "image/heic", "image/heif")
            },
        }
    },
)
async def upload_image(
    request: Request,
    x_filename: str = Header(default="image"),
    x_image_width: str | None = Header(default=None),
    x_image_height: str | None = Header(default=None),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> APIResponse[ImageAssetView]:
    declared = request.headers.get("content-length")
    maximum = get_settings().media_max_image_bytes
    if declared and declared.isdigit() and int(declared) > maximum:
        raise AppError("IMAGE_SIZE_INVALID", f"图片不能超过 {maximum} 字节", 413)
    payload = await request.body()
    asset = service.store_image(
        db,
        user.id,
        payload,
        request.headers.get("content-type", "application/octet-stream"),
        x_filename,
        _optional_positive_int(x_image_width, "X-Image-Width"),
        _optional_positive_int(x_image_height, "X-Image-Height"),
    )
    return APIResponse(data=ImageAssetView.model_validate(service.asset_view(asset)))


@router.get(
    "/images/{asset_id}",
    response_class=FileResponse,
    responses={
        200: {
            "description": "Authenticated image bytes",
            "content": {
                media_type: {"schema": {"type": "string", "format": "binary"}}
                for media_type in ("image/jpeg", "image/png", "image/heic", "image/heif")
            },
        }
    },
)
def download_image(
    asset_id: str,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    asset = service.get_authorized_asset(db, asset_id, user.id)
    return FileResponse(
        path=asset.storage_path,
        media_type=asset.content_type,
        filename=asset.original_filename,
        content_disposition_type="inline",
    )
