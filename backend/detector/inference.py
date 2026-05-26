from __future__ import annotations

import os
from datetime import datetime

from backend.detector.engine import engine
from backend.detector.postprocessing import classify_severity, postprocess_predictions
from backend.detector.preprocessing import prepare_image
from backend.utils.timing import measure_ms


YOLO_CONFIDENCE_THRESHOLD = float(
    os.getenv("YOLO_CONFIDENCE_THRESHOLD", "0.50")
)
YOLO_IMAGE_SIZE = int(os.getenv("YOLO_IMAGE_SIZE", "640"))


def inspect_image(image_path: str) -> dict:
    metadata = prepare_image(image_path)

    with measure_ms() as timer:
        predictions = engine.predict(
            metadata["path"],
            confidence=YOLO_CONFIDENCE_THRESHOLD,
            image_size=YOLO_IMAGE_SIZE,
        )
        model = engine.load()
        defects = postprocess_predictions(predictions, model)

    severity = classify_severity(defects)
    status = "FAIL" if defects else "PASS"

    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "defect_count": len(defects),
        "inference_ms": timer.elapsed_ms,
        "severity": severity,
        "defects": defects,
        "image": {
            "width": metadata["width"],
            "height": metadata["height"],
            "saved_path": metadata["saved_path"],
        },
        "image_path": metadata["path"],
        "source": "yolov8",
        "model_source": "yolov8",
    }
