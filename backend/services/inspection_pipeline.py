# backend/services/inspection_pipeline.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
))

import uuid, random
from datetime import datetime

from ai_core.inference.mock_detector       import mock_detect
from backend.services.severity_engine      import SeverityEngine
from backend.services.root_cause_engine    import RootCauseEngine
from backend.services.notification_service import (
    publish_inspection, publish_alert,
    update_dashboard_stats
)
from backend.services.database_service     import (
    save_inspection, save_alert, get_todays_stats
)

severity_engine   = SeverityEngine()
root_cause_engine = RootCauseEngine()
MACHINES          = ["M-01","M-02","M-03",
                     "M-04","M-05","M-06"]

def run_inspection(image_path: str = None) -> dict:

    machine_id = random.choice(MACHINES)
    detection  = mock_detect(image_path)
    severity   = severity_engine.classify(detection)

    root_cause = None
    if detection["status"] == "FAIL":
        defect_class = detection["defects"][0]["class"]
        root_cause   = root_cause_engine.analyse(
            defect_class, machine_id
        )

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

    # ── SAVE TO POSTGRESQL ───────────────────────────
    save_inspection(result)

    # ── SAVE ALERT IF LEVEL 2+ ───────────────────────
    if severity["level"] >= 2:
        save_alert(result)

    # ── PUBLISH TO REDIS (live dashboard) ────────────
    publish_inspection(result)
    if severity["level"] >= 2:
        publish_alert(result)

    # ── UPDATE DASHBOARD STATS CACHE ─────────────────
    stats = get_todays_stats()
    update_dashboard_stats(stats)

    return result