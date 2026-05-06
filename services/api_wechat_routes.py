"""Wechat Moments API routes."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.api_models import WechatMomentsDraftBody, WechatMomentsExportBody


def create_router(
    get_current_workspace,
    get_wechat_moments_draft,
    get_wechat_moments_status,
    save_wechat_moments_draft,
    export_wechat_moments_image,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/wechat_moments/status")
    async def wechat_moments_status():
        return JSONResponse(get_wechat_moments_status(get_current_workspace()))

    @router.get("/api/wechat_moments/draft")
    async def wechat_moments_draft():
        return JSONResponse(get_wechat_moments_draft(get_current_workspace()))

    @router.put("/api/wechat_moments/draft")
    async def wechat_moments_save_draft(body: WechatMomentsDraftBody):
        try:
            return JSONResponse(save_wechat_moments_draft(body.draft, get_current_workspace()))
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    @router.post("/api/wechat_moments/export")
    async def wechat_moments_export(body: WechatMomentsExportBody):
        try:
            return JSONResponse(
                export_wechat_moments_image(
                    image_data_url=body.image_data_url,
                    draft=body.draft,
                    workspace=get_current_workspace(),
                )
            )
        except Exception as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=400)

    return router
