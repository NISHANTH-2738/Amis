from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter


router = APIRouter()


@router.get("/")
async def root():
    return {
        "system": "Industrial AI Inspection Platform",
        "status": "running",
        "version": "1.0.0",
    }


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
    }
