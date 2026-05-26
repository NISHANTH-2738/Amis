from __future__ import annotations

from typing import Any


SEVERITY_ACTIONS = {
    1: {"name": "LOW", "action": "CONTINUE LINE"},
    2: {"name": "MEDIUM", "action": "OPERATOR REVIEW"},
    3: {"name": "HIGH", "action": "ISOLATE MATERIAL"},
    4: {"name": "CRITICAL", "action": "STOP LINE"},
}


def _class_name(model: Any, class_id: int) -> str:
    names = getattr(model, "names", {})
    if isinstance(names, dict):
        return str(names.get(class_id, class_id))
    if isinstance(names, list) and class_id < len(names):
        return str(names[class_id])
    return str(class_id)


def _clamp_bbox(values: list[float], width: int, height: int) -> list[float]:
    x1, y1, x2, y2 = values
    x1 = max(0.0, min(x1, float(width)))
    y1 = max(0.0, min(y1, float(height)))
    x2 = max(0.0, min(x2, float(width)))
    y2 = max(0.0, min(y2, float(height)))
    return [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]


def postprocess_predictions(predictions, model: Any) -> list[dict]:
    defects: list[dict] = []

    for prediction in predictions:
        height, width = 0, 0
        if getattr(prediction, "orig_shape", None):
            height, width = prediction.orig_shape[:2]

        boxes = getattr(prediction, "boxes", None)
        if boxes is None:
            continue

        for box in boxes:
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])
            x1, y1, x2, y2 = [float(value) for value in box.xyxy[0]]
            if width and height:
                bbox = _clamp_bbox([x1, y1, x2, y2], width, height)
            else:
                bbox = [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]
            defects.append(
                {
                    "class": _class_name(model, class_id),
                    "confidence": round(confidence, 4),
                    "bbox": bbox,
                }
            )

    return defects


def classify_severity(defects: list[dict]) -> dict:
    if not defects:
        action = SEVERITY_ACTIONS[1]
        return {
            "name": action["name"],
            "score": 0.0,
            "level": 1,
            "action": action["action"],
        }

    top_confidence = max(float(item.get("confidence", 0.0)) for item in defects)
    if len(defects) >= 4 or top_confidence >= 0.9:
        level = 4
    elif len(defects) >= 2 or top_confidence >= 0.75:
        level = 3
    elif top_confidence >= 0.5:
        level = 2
    else:
        level = 1

    action = SEVERITY_ACTIONS[level]
    return {
        "name": action["name"],
        "score": round(top_confidence, 4),
        "level": level,
        "action": action["action"],
    }
