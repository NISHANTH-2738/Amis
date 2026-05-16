import os
import uuid
from datetime import datetime
from typing import Awaitable, Callable

from PIL import Image

from ai_core.inference.isolation_forest_detector import detector as isolation_forest
from backend.services.database_service import save_alert, save_inspection
from backend.services.hybrid_detector import hybrid_detect
from backend.services.notification_service import publish_alert, publish_inspection
from backend.services.root_cause_engine import MOCK_MACHINE_STATE, RootCauseEngine
from backend.services.severity_engine import SeverityEngine


severity_engine = SeverityEngine()
root_cause_engine = RootCauseEngine()
DEFAULT_MACHINE_ID = os.getenv("FABRIGUARD_DEFAULT_MACHINE_ID", "M-05")
BroadcastCallback = Callable[[dict], Awaitable[None]]


def _image_metadata(image_path):
    if not image_path or not os.path.exists(image_path):
        return {"width": 416, "height": 416, "saved_path": image_path}
    try:
        with Image.open(image_path) as image:
            return {"width": image.width, "height": image.height, "saved_path": image_path}
    except Exception:
        return {"width": 416, "height": 416, "saved_path": image_path}


def _prediction_from_detection(detection):
    if detection.get("defects"):
        defect = detection["defects"][0]
        return {
            "label": defect.get("class", "unknown_anomaly"),
            "confidence": defect.get("confidence", 0.0),
            "is_defect": True,
            "bbox": defect.get("bbox"),
            "model": detection.get("source", "hybrid_detector"),
        }
    return {
        "label": "normal",
        "confidence": 1.0,
        "is_defect": False,
        "bbox": None,
        "model": detection.get("source", "hybrid_detector"),
    }


def build_websocket_events(result: dict) -> list[dict]:
    defect = result["defects"][0] if result.get("defects") else None
    events = [
        {
            "type": "inspection",
            "inspection_id": result["inspection_id"],
            "timestamp": result["timestamp"],
            "machine_id": result["machine_id"],
            "status": result["status"],
            "defects": result.get("defects", []),
            "severity": result["severity"]["name"],
            "severity_level": result["severity"]["level"],
            "prediction": result.get("prediction"),
            "root_cause": result.get("root_cause"),
            "anomaly": result.get("anomaly"),
            "processing": result.get("processing"),
            "image": result.get("image"),
            "defect": defect.get("class") if defect else None,
            "confidence": defect.get("confidence") if defect else None,
            "bbox": defect.get("bbox") if defect else None,
            "action": result["severity"]["action"],
        }
    ]
    if result["severity"]["level"] >= 2:
        events.append(
            {
                "type": "alert",
                "level": result["severity"]["level"],
                "level_name": result["severity"]["name"],
                "machine_id": result["machine_id"],
                "defect": defect.get("class") if defect else "sensor_anomaly",
                "confidence": defect.get("confidence") if defect else result.get("anomaly", {}).get("score"),
                "action": result["severity"]["action"],
                "root_cause": result["root_cause"]["cause"] if result.get("root_cause") else None,
                "fix": result["root_cause"]["action"] if result.get("root_cause") else None,
                "inspection_id": result["inspection_id"],
                "timestamp": result["timestamp"],
            }
        )
    return events


def build_event(detection, severity, root_cause, anomaly, machine_id, image_path):
    return {
        "frame_id": str(uuid.uuid4()),
        "inspection_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "source": "camera_0",
        "machine_id": machine_id,
        "status": detection["status"],
        "defects": detection.get("defects", []),
        "prediction": _prediction_from_detection(detection),
        "severity": severity,
        "root_cause": root_cause,
        "anomaly": {
            "score": anomaly.get("score", 0.0),
            "is_anomaly": anomaly.get("is_anomaly", False),
            "model": anomaly.get("model", "isolation_forest"),
            "violations": anomaly.get("violations", []),
        },
        "patchcore": detection.get(
            "patchcore",
            {"anomaly_score": 0.0, "is_anomaly": False, "heatmap_path": None},
        ),
        "image": _image_metadata(image_path),
        "processing": {
            "latency_ms": detection.get("inference_ms", 0),
            "device": "cpu",
            "model_source": detection.get("source", "hybrid_detector"),
        },
        "inference_ms": detection.get("inference_ms", 0),
        "model_source": detection.get("source", "hybrid_detector"),
    }


def process_frame(frame=None, machine_id: str | None = None, sensor_state: dict | None = None, image_path: str | None = None) -> dict:
    machine_id = machine_id or DEFAULT_MACHINE_ID
    sensor_state = sensor_state or MOCK_MACHINE_STATE.get(machine_id, {})

    detection = hybrid_detect(image_path)
    anomaly = isolation_forest.check_machine(machine_id, sensor_state)
    severity = severity_engine.classify(detection, anomaly)

    root_cause = None
    if detection["status"] == "FAIL":
        defect_class = detection["defects"][0].get("class", "unknown_anomaly")
        root_cause = root_cause_engine.analyse(defect_class, machine_id, sensor_state)

    return build_event(detection, severity, root_cause, anomaly, machine_id, image_path)


async def run_inspection_flow(
    image_path: str = None,
    machine_id: str | None = None,
    broadcast: BroadcastCallback | None = None,
) -> dict:
    result = process_frame(image_path=image_path, machine_id=machine_id)
    save_inspection(result)
    save_alert(result)
    publish_inspection(result)
    publish_alert(result)
    if broadcast:
        for event in build_websocket_events(result):
            await broadcast(event)
    return result


def run_inspection(image_path: str = None) -> dict:
    """Synchronous compatibility path for simulator and older endpoints."""
    result = process_frame(image_path=image_path)
    save_inspection(result)
    save_alert(result)
    publish_inspection(result)
    publish_alert(result)
    return result
