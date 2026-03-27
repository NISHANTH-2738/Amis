# backend/services/inspection_pipeline.py

import uuid
import random
from datetime import datetime

from ai_core.inference.mock_detector import mock_detect# LATER: from ai_core.inference.yolo_detector import yolo_detect

from backend.services.severity_engine    import SeverityEngine
from backend.services.root_cause_engine  import RootCauseEngine

severity_engine   = SeverityEngine()
root_cause_engine = RootCauseEngine()

MACHINES = ["M-01","M-02","M-03","M-04","M-05","M-06"]

def run_inspection(image_path: str = None) -> dict:
    """
    Full pipeline — one call does everything.
    Swap mock_detect → yolo_detect when model is ready.
    Nothing else changes.
    """

    machine_id = random.choice(MACHINES)

    # ── STEP 1: DETECT ──────────────────────────────
    detection = mock_detect(image_path)
    # detection = yolo_detect(image_path)  ← swap here later

    # ── STEP 2: CLASSIFY SEVERITY ───────────────────
    severity = severity_engine.classify(detection)

    # ── STEP 3: ROOT CAUSE (only if defect found) ───
    root_cause = None
    if detection["status"] == "FAIL":
        defect_class = detection["defects"][0]["class"]
        root_cause   = root_cause_engine.analyse(
            defect_class, machine_id
        )

    # ── STEP 4: BUILD FULL RESULT ───────────────────
    result = {
        "inspection_id": str(uuid.uuid4())[:8],
        "timestamp":     datetime.now().isoformat(),
        "machine_id":    machine_id,
        "status":        detection["status"],
        "defects":       detection["defects"],
        "severity":      severity,
        "root_cause":    root_cause,
        "inference_ms":  detection["inference_ms"],
        "model_source":  detection["source"],
    }

    return result