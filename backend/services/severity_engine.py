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
        1: {"name": "MONITOR", "action": "CONTINUE LINE"},
        2: {"name": "WARNING", "action": "OPERATOR REVIEW"},
        3: {"name": "CRITICAL", "action": "ISOLATE MATERIAL"},
        4: {"name": "EMERGENCY", "action": "STOP LINE"},
    }

    def _bbox_area(self, bbox) -> float:
        if isinstance(bbox, dict):
            return float(bbox.get("width", 0.0)) * float(bbox.get("height", 0.0))
        if isinstance(bbox, list) and len(bbox) == 4:
            x1, y1, x2, y2 = [float(value) for value in bbox]
            return max(0.0, x2 - x1) * max(0.0, y2 - y1)
        return 0.0

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
                "action": "CONTINUE LINE",
                "defect": None,
                "confidence": 1.0,
                "escalated": False,
            }

        defects = detection.get("defects") or [{}]
        defect = max(defects, key=lambda item: float(item.get("confidence", 0.0)))
        defect_class = defect.get("class", "unknown_anomaly")
        confidence = float(defect.get("confidence", 0.0))
        bbox_area = self._bbox_area(defect.get("bbox"))
        patchcore = detection.get("patchcore") or {}

        rule = self.LEVEL_RULES.get(defect_class, {"base_level": 2, "critical_conf": 0.85})
        level = int(rule["base_level"])
        if confidence >= float(rule["critical_conf"]):
            level = min(level + 1, 4)
        if len(defects) >= 3:
            level = min(level + 1, 4)
        if bbox_area >= 20000:
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
