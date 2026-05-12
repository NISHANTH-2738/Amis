import json
import time
from pathlib import Path

from ai_core.inference.mock_detector import mock_detect


DEFAULT_WEIGHTS = Path("ai_core/models/fabriguard_v1/weights/best.pt")
DEFAULT_LABEL_MAP = Path("ai_core/data/processed/label_map.json")

_model = None
_model_path = None


def _load_label_map(path: Path = DEFAULT_LABEL_MAP):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {int(k): v for k, v in data.items()}


def load_model(weights_path: str | Path = DEFAULT_WEIGHTS, force: bool = False):
    global _model, _model_path
    weights_path = Path(weights_path)
    if _model is not None and _model_path == weights_path and not force:
        return _model
    if not weights_path.exists():
        return None
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    _model = YOLO(str(weights_path))
    _model_path = weights_path
    return _model


def model_status(weights_path: str | Path = DEFAULT_WEIGHTS):
    weights_path = Path(weights_path)
    return {
        "primary_model": "yolov5n",
        "weights_path": str(weights_path),
        "weights_available": weights_path.exists(),
        "loaded": _model is not None,
        "fallback": "mock_detector" if not weights_path.exists() else None,
    }


def _normalize_bbox(x1, y1, x2, y2, width, height):
    return {
        "x": round(float(x1) / width, 6),
        "y": round(float(y1) / height, 6),
        "width": round(float(x2 - x1) / width, 6),
        "height": round(float(y2 - y1) / height, 6),
    }


def yolo_detect(image_path: str | None = None, confidence_threshold: float = 0.25) -> dict:
    started = time.perf_counter()
    model = load_model()
    if model is None or image_path is None:
        result = mock_detect(image_path)
        result["source"] = "mock_yolo_fallback"
        return result

    predictions = model(str(image_path), imgsz=416, conf=confidence_threshold, device="cpu", verbose=False)
    label_map = _load_label_map()
    defects = []
    width = height = 416

    for prediction in predictions:
        if getattr(prediction, "orig_shape", None):
            height, width = prediction.orig_shape[:2]
        boxes = getattr(prediction, "boxes", None)
        if boxes is None:
            continue
        for box in boxes:
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            defects.append(
                {
                    "class": label_map.get(class_id, getattr(model, "names", {}).get(class_id, str(class_id))),
                    "confidence": round(confidence, 4),
                    "bbox": _normalize_bbox(x1, y1, x2, y2, width, height),
                    "severity_weight": round(min(1.0, confidence), 4),
                }
            )

    return {
        "status": "FAIL" if defects else "PASS",
        "defects": defects,
        "inference_ms": int((time.perf_counter() - started) * 1000),
        "image_path": image_path,
        "source": "yolov5n",
    }


def reload_model(weights_path: str | Path = DEFAULT_WEIGHTS):
    model = load_model(weights_path, force=True)
    return model_status(weights_path) | {"reloaded": model is not None}
