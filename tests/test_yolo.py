import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from ai_core.inference.yolo_detector import model_status, yolo_detect


def test_yolo_fallback_contract():
    status = model_status()
    assert status["primary_model"] == "yolov5n"

    result = yolo_detect(None)
    assert result["status"] in {"PASS", "FAIL"}
    assert "defects" in result
    assert "inference_ms" in result
    assert result["source"] in {"yolov5n", "mock_yolo_fallback"}
