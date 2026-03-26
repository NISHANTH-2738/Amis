# backend/services/severity_engine.py

class SeverityEngine:
    """
    Takes detector output (mock or real — same format).
    Decides what level of response is needed.
    This logic is 100% real and stays unchanged forever.
    """

    LEVEL_RULES = {
        "drop_stitch":  {"base_level": 2, "critical_conf": 0.85},
        "hole":         {"base_level": 3, "critical_conf": 0.75},
        "needle_line":  {"base_level": 2, "critical_conf": 0.90},
        "run_ladder":   {"base_level": 3, "critical_conf": 0.80},
        "stain":        {"base_level": 2, "critical_conf": 0.85},
        "pilling":      {"base_level": 1, "critical_conf": 0.95},
        "tuck_fault":   {"base_level": 1, "critical_conf": 0.90},
        "fly_yarn":     {"base_level": 1, "critical_conf": 0.95},
    }

    LEVEL_ACTIONS = {
        1: {"name": "MONITOR",  "action": "Log silently. Continue production."},
        2: {"name": "ALERT",    "action": "Flag product. Notify inspector tablet."},
        3: {"name": "ISOLATE",  "action": "Divert to rework. Alert supervisor."},
        4: {"name": "STOP",     "action": "Halt line. Quarantine batch. Escalate."},
    }

    def classify(self, detection: dict) -> dict:
        if detection["status"] == "PASS":
            return {"level": 0, "name": "PASS", "action": "Continue"}

        defect    = detection["defects"][0]
        defect_class = defect["class"]
        confidence   = defect["confidence"]

        rule  = self.LEVEL_RULES.get(defect_class, {"base_level": 2, "critical_conf": 0.85})
        level = rule["base_level"]

        # Escalate if very high confidence
        if confidence >= rule["critical_conf"]:
            level = min(level + 1, 4)

        return {
            "level":       level,
            "name":        self.LEVEL_ACTIONS[level]["name"],
            "action":      self.LEVEL_ACTIONS[level]["action"],
            "defect":      defect_class,
            "confidence":  confidence,
            "escalated":   confidence >= rule["critical_conf"]
        }