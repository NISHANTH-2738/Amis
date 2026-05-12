from ai_core.inference.patchcore_detector import patchcore
from ai_core.inference.yolo_detector import yolo_detect


def hybrid_detect(image_path: str | None = None) -> dict:
    detection = yolo_detect(image_path)
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
            detection["source"] = "hybrid_yolo_patchcore"

    return detection
