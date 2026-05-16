"""Roboflow hosted inference adapter for FabriGuard.

This module owns the network boundary to Roboflow. The rest of the backend
receives a small, stable detection format, so the inspection pipeline,
severity engine, database writes, and websocket events do not need to know
which hosted model or SDK is used.
"""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from PIL import Image

load_dotenv()

LOGGER = logging.getLogger(__name__)

ROBOFLOW_API_URL = os.getenv("ROBOFLOW_API_URL", "https://serverless.roboflow.com")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID")
ROBOFLOW_WORKSPACE_NAME = os.getenv("ROBOFLOW_WORKSPACE_NAME")
ROBOFLOW_WORKFLOW_ID = os.getenv("ROBOFLOW_WORKFLOW_ID")
ROBOFLOW_WORKFLOW_IMAGE_KEY = os.getenv("ROBOFLOW_WORKFLOW_IMAGE_KEY", "image")
ROBOFLOW_TIMEOUT_SECONDS = float(os.getenv("ROBOFLOW_TIMEOUT_SECONDS", "8"))
ROBOFLOW_CONFIDENCE_THRESHOLD = float(os.getenv("ROBOFLOW_CONFIDENCE_THRESHOLD", "0.35"))
ROBOFLOW_MAX_IMAGE_SIZE = int(os.getenv("ROBOFLOW_MAX_IMAGE_SIZE", "640"))
ROBOFLOW_JPEG_QUALITY = int(os.getenv("ROBOFLOW_JPEG_QUALITY", "72"))
ROBOFLOW_CACHE_SIZE = int(os.getenv("ROBOFLOW_CACHE_SIZE", "128"))

_client = None
_cache: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="roboflow")


@dataclass(frozen=True)
class PreparedImage:
    path: str
    original_width: int
    original_height: int
    sent_width: int
    sent_height: int


def _get_client():
    """Initialize the Roboflow SDK lazily so local tests can run without it."""
    global _client
    if _client is not None:
        return _client
    has_workflow = ROBOFLOW_WORKSPACE_NAME and ROBOFLOW_WORKFLOW_ID
    has_model = ROBOFLOW_MODEL_ID
    if not ROBOFLOW_API_KEY or not (has_workflow or has_model):
        LOGGER.warning(
            "Roboflow disabled: set ROBOFLOW_API_KEY and either "
            "ROBOFLOW_WORKSPACE_NAME plus ROBOFLOW_WORKFLOW_ID, or ROBOFLOW_MODEL_ID in .env"
        )
        return None
    try:
        from inference_sdk import InferenceHTTPClient
    except ImportError:
        LOGGER.warning("Roboflow disabled: install inference-sdk")
        return None

    _client = InferenceHTTPClient(api_url=ROBOFLOW_API_URL, api_key=ROBOFLOW_API_KEY)
    return _client


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cache_key(image_path: str) -> str:
    return "|".join(
        [
            _file_hash(image_path),
            ROBOFLOW_MODEL_ID or "",
            ROBOFLOW_WORKSPACE_NAME or "",
            ROBOFLOW_WORKFLOW_ID or "",
            str(ROBOFLOW_CONFIDENCE_THRESHOLD),
            str(ROBOFLOW_MAX_IMAGE_SIZE),
            str(ROBOFLOW_JPEG_QUALITY),
        ]
    )


def _cache_get(key: str) -> list[dict[str, Any]] | None:
    cached = _cache.get(key)
    if cached is None:
        return None
    _cache.move_to_end(key)
    return [item.copy() for item in cached]


def _cache_set(key: str, detections: list[dict[str, Any]]) -> None:
    _cache[key] = [item.copy() for item in detections]
    _cache.move_to_end(key)
    while len(_cache) > ROBOFLOW_CACHE_SIZE:
        _cache.popitem(last=False)


def _prepare_image(image_path: str) -> PreparedImage:
    """Resize and JPEG-compress before upload to reduce bandwidth and latency."""
    source = Path(image_path)
    if not source.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(source) as image:
        image = image.convert("RGB")
        original_width, original_height = image.size
        image.thumbnail((ROBOFLOW_MAX_IMAGE_SIZE, ROBOFLOW_MAX_IMAGE_SIZE), Image.Resampling.LANCZOS)
        sent_width, sent_height = image.size

        temp_file = tempfile.NamedTemporaryFile(prefix="fabriguard_rf_", suffix=".jpg", delete=False)
        temp_file.close()
        image.save(temp_file.name, format="JPEG", quality=ROBOFLOW_JPEG_QUALITY, optimize=True)

    return PreparedImage(
        path=temp_file.name,
        original_width=original_width,
        original_height=original_height,
        sent_width=sent_width,
        sent_height=sent_height,
    )


def _scale_bbox_to_original(prediction: dict[str, Any], prepared: PreparedImage) -> list[float]:
    x = float(prediction.get("x", 0.0))
    y = float(prediction.get("y", 0.0))
    width = float(prediction.get("width", 0.0))
    height = float(prediction.get("height", 0.0))

    x1 = max(0.0, x - width / 2)
    y1 = max(0.0, y - height / 2)
    x2 = min(float(prepared.sent_width), x + width / 2)
    y2 = min(float(prepared.sent_height), y + height / 2)

    scale_x = prepared.original_width / max(prepared.sent_width, 1)
    scale_y = prepared.original_height / max(prepared.sent_height, 1)

    return [
        round(x1 * scale_x, 2),
        round(y1 * scale_y, 2),
        round(x2 * scale_x, 2),
        round(y2 * scale_y, 2),
    ]


def _collect_predictions(result: Any) -> list[dict[str, Any]]:
    """Find detection-like prediction lists in Roboflow model or workflow output."""
    if isinstance(result, list):
        predictions = []
        for item in result:
            predictions.extend(_collect_predictions(item))
        return predictions
    if not isinstance(result, dict):
        return []

    direct = result.get("predictions")
    if isinstance(direct, list):
        return [item for item in direct if isinstance(item, dict)]

    predictions = []
    for value in result.values():
        if isinstance(value, (dict, list)):
            predictions.extend(_collect_predictions(value))
    return predictions


def _standardize_predictions(result: Any, prepared: PreparedImage) -> list[dict[str, Any]]:
    predictions = _collect_predictions(result)
    detections = []
    for prediction in predictions:
        confidence = float(prediction.get("confidence", 0.0))
        if confidence < ROBOFLOW_CONFIDENCE_THRESHOLD:
            continue
        detections.append(
            {
                "class": str(prediction.get("class") or prediction.get("class_name") or "unknown_anomaly"),
                "confidence": round(confidence, 4),
                "bbox": _scale_bbox_to_original(prediction, prepared),
            }
        )
    return detections


def detect_defects(image_path: str) -> list[dict[str, Any]]:
    """Run Roboflow inference and return FabriGuard's standard detection list.

    On API, SDK, timeout, or image errors this returns an empty list. That keeps
    the inspection loop and dashboard websocket alive even if the hosted model
    is temporarily unavailable.
    """
    started = time.perf_counter()
    client = _get_client()
    if client is None:
        return []

    try:
        key = _cache_key(image_path)
        cached = _cache_get(key)
        if cached is not None:
            return cached

        prepared = _prepare_image(image_path)
        try:
            if ROBOFLOW_WORKSPACE_NAME and ROBOFLOW_WORKFLOW_ID:
                future = _executor.submit(
                    client.run_workflow,
                    workspace_name=ROBOFLOW_WORKSPACE_NAME,
                    workflow_id=ROBOFLOW_WORKFLOW_ID,
                    images={ROBOFLOW_WORKFLOW_IMAGE_KEY: prepared.path},
                    use_cache=True,
                )
            else:
                future = _executor.submit(client.infer, prepared.path, model_id=ROBOFLOW_MODEL_ID)
            result = future.result(timeout=ROBOFLOW_TIMEOUT_SECONDS)
            detections = _standardize_predictions(result, prepared)
            _cache_set(key, detections)
            LOGGER.info("Roboflow inference completed in %.0fms", (time.perf_counter() - started) * 1000)
            return detections
        finally:
            try:
                os.unlink(prepared.path)
            except OSError:
                pass
    except TimeoutError:
        LOGGER.warning("Roboflow inference timed out after %.1fs", ROBOFLOW_TIMEOUT_SECONDS)
    except Exception as exc:
        LOGGER.warning("Roboflow inference failed: %s", exc)
    return []
