"""Model configuration API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.api.models import ModelConfigBody
from backend.services.model_config import (
    clear_model_config,
    load_model_config,
    save_model_config,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/model-config", tags=["model-config"])


@router.get("")
async def get_model_config():
    try:
        return JSONResponse(load_model_config())
    except Exception as exc:
        logger.error(f"Failed to load model config: {exc}")
        return JSONResponse({"baseUrl": "", "model": "", "apiKey": ""})


@router.post("")
@router.put("")
async def update_model_config(body: ModelConfigBody):
    try:
        return JSONResponse(save_model_config(body.model_dump()))
    except Exception as exc:
        logger.error(f"Failed to save model config: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.delete("")
async def delete_model_config():
    try:
        clear_model_config()
        return JSONResponse({"ok": True, "message": "Model config cleared"})
    except Exception as exc:
        logger.error(f"Failed to clear model config: {exc}")
        return JSONResponse({"error": str(exc)}, status_code=500)
