from __future__ import annotations

import base64
import os
import uuid
from datetime import datetime

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

from backend.api.websocket.manager import dashboard_manager
from backend.detector.engine import ModelUnavailableError
from backend.services.inspection_pipeline import run_inspection_flow


router = APIRouter()


def _safe_upload_path(folder: str, filename: str) -> str:
    os.makedirs(folder, exist_ok=True)
    safe_name = (filename or "inspection.jpg").replace(" ", "_")
    return os.path.join(folder, f"{uuid.uuid4()}_{safe_name}")


async def _inspect_upload(file: UploadFile, folder: str):
    image_path = _safe_upload_path(folder, file.filename)
    try:
        with open(image_path, "wb") as output:
            output.write(await file.read())
        return await run_inspection_flow(
            image_path,
            broadcast=dashboard_manager.broadcast,
        )
    except ModelUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "ERROR",
                "error": "model_unavailable",
                "message": str(exc),
                "timestamp": datetime.now().isoformat(),
            },
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={
                "status": "ERROR",
                "error": "invalid_image",
                "message": str(exc),
                "timestamp": datetime.now().isoformat(),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "status": "ERROR",
                "error": "inspection_failed",
                "message": "Inspection failed safely",
                "detail": str(exc),
                "timestamp": datetime.now().isoformat(),
            },
        )
    finally:
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
        except OSError:
            pass


@router.post("/inspect-image")
async def inspect_image(file: UploadFile = File(...)):
    return await _inspect_upload(file, "uploads/inspect")


@router.post("/inspect/frame")
async def inspect_frame(file: UploadFile = File(...)):
    return await _inspect_upload(file, "uploads/frame")


@router.post("/inspect")
async def inspect(file: UploadFile = File(...)):
    return await _inspect_upload(file, "uploads")


@router.post("/inspect/webcam")
async def inspect_webcam(image_data: str | None = None):
    if not image_data:
        return JSONResponse(
            status_code=400,
            content={"error": "No image data"},
        )

    try:
        payload = image_data.split(",", 1)[1] if "," in image_data else image_data
        image_bytes = base64.b64decode(payload)
        os.makedirs("uploads/webcam", exist_ok=True)
        image_path = f"uploads/webcam/{uuid.uuid4()}.jpg"
        with open(image_path, "wb") as output:
            output.write(image_bytes)
        with Image.open(image_path) as image:
            image.verify()
        return await run_inspection_flow(
            image_path,
            broadcast=dashboard_manager.broadcast,
        )
    except ModelUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content={
                "status": "ERROR",
                "error": "model_unavailable",
                "message": str(exc),
            },
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )
    finally:
        try:
            if "image_path" in locals() and os.path.exists(image_path):
                os.remove(image_path)
        except OSError:
            pass
