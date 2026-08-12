"""Internal HTTP surface for Campus MCP (sidecar-only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import Field
from sqlalchemy.orm import Session

from onemore.core.config import get_settings
from onemore.core.database import get_db
from onemore.core.errors import AppError
from onemore.core.schemas import APIModel, APIResponse
from onemore.hermes.campus_mcp import dispatch_tool, list_tools_public

router = APIRouter(prefix="/internal/campus-mcp", tags=["campus-mcp"])


class ToolCallRequest(APIModel):
    name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)
    tool_session: str = Field(min_length=8, max_length=128)


def require_campus_mcp_token(
    x_campus_mcp_token: str | None = Header(default=None, alias="X-Campus-MCP-Token"),
) -> None:
    settings = get_settings()
    expected = (settings.campus_mcp_token or "").strip()
    if settings.env == "test":
        return
    if not expected:
        if settings.is_production:
            raise AppError("MCP_TOKEN_MISSING", "Campus MCP 未配置共享密钥", 503)
        return
    if (x_campus_mcp_token or "").strip() != expected:
        raise AppError("MCP_UNAUTHORIZED", "Campus MCP 鉴权失败", 401)


@router.get("/tools", response_model=APIResponse[list[dict]], dependencies=[Depends(require_campus_mcp_token)])
def list_campus_tools() -> APIResponse[list[dict]]:
    return APIResponse(data=list_tools_public())


@router.get("/openai-tools", response_model=APIResponse[list[dict]], dependencies=[Depends(require_campus_mcp_token)])
def openai_tools() -> APIResponse[list[dict]]:
    from onemore.hermes.campus_mcp import openai_tool_schemas

    return APIResponse(data=openai_tool_schemas())


@router.post("/tools/call", response_model=APIResponse[dict], dependencies=[Depends(require_campus_mcp_token)])
def call_campus_tool(body: ToolCallRequest, db: Session = Depends(get_db)) -> APIResponse[dict]:
    return APIResponse(
        data=dispatch_tool(body.name, body.arguments, tool_session=body.tool_session, db=db)
    )
