import time
from pathlib import Path

from PIL import Image

from ai_core.inference.patchcore_detector import patchcore
from backend.services.roboflow_service import detect_defects


def hybrid_detect(image_path: str | None = None) -> dict:
    detection = _roboflow_detect(image_path)
    detection.setdefault(
        "patchcore",
        {"anomaly_score": 0.0, "is_anomaly": False, "heatmap_path": None},
    )

    low_confidence = any(defect.get("confidence", 0) < 0.35 for defect in detection.get("defects", []))
    if detection["status"] == "PASS" or low_confidence:
        patchcore_result = patchcore.inspect(image_path) if image_path else {
            "status": "PASS",
            "defects": [],
            "inference_ms": 0,
            "source": "patchcore_no_image",
            "patchcore": {"anomaly_score": 0.0, "is_anomaly": False, "heatmap_path": None},
        }
        detection["patchcore"] = patchcore_result.get("patchcore", {})
        if patchcore_result["status"] == "FAIL" and detection["status"] == "PASS":
            detection = patchcore_result
            detection["source"] = "hybrid_patchcore"
        else:
            detection["inference_ms"] += patchcore_result.get("inference_ms", 0)
            detection["source"] = "hybrid_roboflow_patchcore"

    return detection


def _image_size(image_path: str | None) -> tuple[int, int]:
    if not image_path or not Path(image_path).exists():
        return 416, 416
    try:
        with Image.open(image_path) as image:
            return image.width, image.height
    except Exception:
        return 416, 416


def _normalize_xyxy(bbox: list[float], width: int, height: int) -> dict:
    x1, y1, x2, y2 = bbox
    return {
        "x": round(max(0.0, min(float(x1) / width, 1.0)), 6),
        "y": round(max(0.0, min(float(y1) / height, 1.0)), 6),
        "width": round(max(0.0, min(float(x2 - x1) / width, 1.0)), 6),
        "height": round(max(0.0, min(float(y2 - y1) / height, 1.0)), 6),
    }


def _roboflow_detect(image_path: str | None = None) -> dict:
    started = time.perf_counter()
    if not image_path:
        return {
            "status": "PASS",
            "defects": [],
            "inference_ms": 0,
            "image_path": image_path,
            "source": "roboflow_no_image",
        }

    width, height = _image_size(image_path)
    detections = detect_defects(image_path)
    defects = [
        {
            "class": detection["class"],
            "confidence": detection["confidence"],
            "bbox": _normalize_xyxy(detection["bbox"], width, height),
            "severity_weight": round(min(1.0, float(detection["confidence"])), 4),
        }
        for detection in detections
    ]

    return {
        "status": "FAIL" if defects else "PASS",
        "defects": defects,
        "inference_ms": int((time.perf_counter() - started) * 1000),
        "image_path": image_path,
        "source": "roboflow",
    }
