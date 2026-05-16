"""Hybrid detector boundary for hosted visual inference.

FabriGuard runs on low-end CPU hardware, so visual detection stays hosted in
Roboflow. This module validates Roboflow output and keeps the downstream
pipeline independent from SDK-specific response shapes.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image

from ai_core.inference.patchcore_detector import patchcore
from backend.services.roboflow_service import detect_defects


LOGGER = logging.getLogger(__name__)


def _image_size(image_path: str | None) -> tuple[int, int]:
    if not image_path or not Path(image_path).exists():
        return 416, 416
    try:
        with Image.open(image_path) as image:
            return image.width, image.height
    except Exception as exc:
        LOGGER.warning("Could not read image size for %s: %s", image_path, exc)
        return 416, 416


def _valid_bbox(bbox: Any, width: int, height: int) -> list[float] | None:
    if isinstance(bbox, dict):
        try:
            x = float(bbox.get("x", 0.0))
            y = float(bbox.get("y", 0.0))
            box_width = float(bbox.get("width", 0.0))
            box_height = float(bbox.get("height", 0.0))
        except (TypeError, ValueError):
            return None
        if 0 <= x <= 1 and 0 <= y <= 1 and box_width <= 1 and box_height <= 1:
            x *= width
            y *= height
            box_width *= width
            box_height *= height
        return _valid_bbox([x, y, x + box_width, y + box_height], width, height)

    if not isinstance(bbox, list) or len(bbox) != 4:
        return None
    try:
        x1, y1, x2, y2 = [float(value) for value in bbox]
    except (TypeError, ValueError):
        return None

    x1 = max(0.0, min(x1, float(width)))
    y1 = max(0.0, min(y1, float(height)))
    x2 = max(0.0, min(x2, float(width)))
    y2 = max(0.0, min(y2, float(height)))
    if x2 <= x1 or y2 <= y1:
        return None
    return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]


def _normalise_detections(raw: list[dict[str, Any]], width: int, height: int) -> list[dict[str, Any]]:
    defects = []
    for item in raw:
        bbox = _valid_bbox(item.get("bbox"), width, height)
        if bbox is None:
            continue
        confidence = max(0.0, min(float(item.get("confidence", 0.0)), 1.0))
        defects.append(
            {
                "class": str(item.get("class") or "unknown_anomaly"),
                "confidence": round(confidence, 4),
                "bbox": bbox,
            }
        )
    return defects


def hybrid_detect(image_path: str | None = None) -> dict:
    started = time.perf_counter()
    width, height = _image_size(image_path)

    if not image_path:
        return {
            "status": "PASS",
            "defects": [],
            "inference_ms": 0,
            "image_path": image_path,
            "source": "roboflow_no_image",
            "patchcore": {"anomaly_score": 0.0, "is_anomaly": False, "heatmap_path": None},
        }

    raw_detections = detect_defects(image_path)
    defects = _normalise_detections(raw_detections, width, height)
    status = "FAIL" if defects else "PASS"
    patchcore_result = {"patchcore": {"anomaly_score": 0.0, "is_anomaly": False, "heatmap_path": None}, "inference_ms": 0}

    # PatchCore is kept as a lightweight secondary guardrail. It only escalates
    # when Roboflow sees no visual defect or returns a weak result.
    low_confidence = any(defect["confidence"] < 0.35 for defect in defects)
    if status == "PASS" or low_confidence:
        try:
            patchcore_result = patchcore.inspect(image_path)
        except Exception as exc:
            LOGGER.warning("PatchCore fallback failed: %s", exc)

    if status == "PASS" and patchcore_result.get("status") == "FAIL":
        defects = _normalise_detections(patchcore_result.get("defects", []), width, height)
        status = "FAIL" if defects else "PASS"

    return {
        "status": status,
        "defects": defects,
        "inference_ms": int((time.perf_counter() - started) * 1000),
        "image_path": image_path,
        "source": "hybrid_roboflow_patchcore",
        "patchcore": patchcore_result.get("patchcore", {}),
    }
