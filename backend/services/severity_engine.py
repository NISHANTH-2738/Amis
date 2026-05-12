class SeverityEngine:
    """Four-level FabriGuard severity treatment for detector and anomaly output."""

    LEVEL_RULES = {
        "drop_stitch": {"base_level": 2, "critical_conf": 0.85},
        "hole": {"base_level": 3, "critical_conf": 0.75},
        "needle_line": {"base_level": 2, "critical_conf": 0.90},
        "run_ladder": {"base_level": 3, "critical_conf": 0.80},
        "stain": {"base_level": 2, "critical_conf": 0.85},
        "pilling": {"base_level": 1, "critical_conf": 0.95},
        "tuck_fault": {"base_level": 1, "critical_conf": 0.90},
        "fly_yarn": {"base_level": 1, "critical_conf": 0.95},
        "unknown_anomaly": {"base_level": 2, "critical_conf": 0.80},
    }

    LEVEL_ACTIONS = {
        1: {"name": "MONITOR", "action": "Log silently. Continue production."},
        2: {"name": "REVIEW", "action": "Flag product for operator review."},
        3: {"name": "ISOLATE", "action": "Divert to rework. Alert supervisor."},
        4: {"name": "REJECT", "action": "Reject item or halt line according to machine workflow."},
    }

    def classify(self, detection: dict, anomaly: dict | None = None) -> dict:
        if detection.get("status") == "PASS":
            if anomaly and anomaly.get("is_anomaly"):
                action = self.LEVEL_ACTIONS[2]
                return {
                    "level": 2,
                    "name": action["name"],
                    "action": action["action"],
                    "defect": "sensor_anomaly",
                    "confidence": abs(float(anomaly.get("score", 0.0))),
                    "escalated": True,
                }
            action = self.LEVEL_ACTIONS[1]
            return {
                "level": 1,
                "name": action["name"],
                "action": "Log clean frame. Continue production.",
                "defect": None,
                "confidence": 1.0,
                "escalated": False,
            }

        defect = (detection.get("defects") or [{}])[0]
        defect_class = defect.get("class", "unknown_anomaly")
        confidence = float(defect.get("confidence", 0.0))
        bbox = defect.get("bbox") or {}
        bbox_area = float(bbox.get("width", 0.0)) * float(bbox.get("height", 0.0))
        patchcore = detection.get("patchcore") or {}

        rule = self.LEVEL_RULES.get(defect_class, {"base_level": 2, "critical_conf": 0.85})
        level = int(rule["base_level"])
        if confidence >= float(rule["critical_conf"]):
            level = min(level + 1, 4)
        if bbox_area >= 0.08:
            level = min(level + 1, 4)
        if patchcore.get("is_anomaly") and float(patchcore.get("anomaly_score", 0.0)) > 60:
            level = min(level + 1, 4)
        if anomaly and len(anomaly.get("violations", [])) >= 2:
            level = min(level + 1, 4)

        action = self.LEVEL_ACTIONS[level]
        return {
            "level": level,
            "name": action["name"],
            "action": action["action"],
            "defect": defect_class,
            "confidence": confidence,
            "escalated": level >= 3,
        }
