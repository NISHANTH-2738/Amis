# backend/services/root_cause_engine.py

from datetime import datetime

# Simulated machine sensor state
# In production this comes from IIoT / MES
MOCK_MACHINE_STATE = {
    "M-01": {"tool_age_days": 3, "vibration": 1.0, "tension_kn": 4.2, "temperature_c": 58},
    "M-02": {"tool_age_days": 5, "vibration": 2.1, "tension_kn": 4.6, "temperature_c": 61},
    "M-03": {"tool_age_days": 1, "vibration": 0.9, "tension_kn": 4.1, "temperature_c": 57},
    "M-04": {"tool_age_days": 8, "vibration": 1.8, "tension_kn": 4.9, "temperature_c": 65},
    "M-05": {"tool_age_days": 2, "vibration": 1.0, "tension_kn": 4.2, "temperature_c": 58},
    "M-06": {"tool_age_days": 4, "vibration": 1.1, "tension_kn": 4.3, "temperature_c": 59},
}

# Defect → probable cause rules
# Based on textile engineering knowledge
CAUSE_RULES = {
    "needle_line": [
        {"condition": lambda s: s["tool_age_days"] > 7,
         "cause":  "Needle overdue for replacement",
         "action": "Replace needle immediately",
         "confidence": 0.91},
        {"condition": lambda s: s["vibration"] > 1.5,
         "cause":  "Excessive machine vibration bending needle",
         "action": "Inspect and tighten machine mounts",
         "confidence": 0.78},
    ],
    "drop_stitch": [
        {"condition": lambda s: s["tension_kn"] > 4.5,
         "cause":  "Warp tension too high — thread skipping",
         "action": "Reduce tension to 4.2 kN baseline",
         "confidence": 0.85},
        {"condition": lambda s: s["temperature_c"] > 63,
         "cause":  "Motor overheating affecting timing",
         "action": "Check cooling fan. Rest machine 10 min.",
         "confidence": 0.72},
    ],
    "hole": [
        {"condition": lambda s: s["tool_age_days"] > 6,
         "cause":  "Worn needle tip causing thread breaks",
         "action": "Replace needle. Inspect thread path.",
         "confidence": 0.88},
        {"condition": lambda s: s["vibration"] > 1.8,
         "cause":  "High vibration causing misalignment",
         "action": "Balance machine. Check bearings.",
         "confidence": 0.76},
    ],
    "run_ladder": [
        {"condition": lambda s: s["tension_kn"] > 4.4,
         "cause":  "Excess tension causing chain stitch failure",
         "action": "Recalibrate tension to 4.1–4.3 kN",
         "confidence": 0.83},
    ],
    "stain": [
        {"condition": lambda s: s["tool_age_days"] > 5,
         "cause":  "Worn parts causing oil leakage onto fabric",
         "action": "Inspect oil seals. Clean fabric path.",
         "confidence": 0.79},
    ],
}

class RootCauseEngine:

    def analyse(self, defect_class: str,
                machine_id: str) -> dict:
        """
        Given a defect type and machine ID:
        → Reads machine sensor state
        → Matches against cause rules
        → Returns most probable cause + action
        """
        state = MOCK_MACHINE_STATE.get(
            machine_id,
            {"tool_age_days":0,"vibration":1.0,
             "tension_kn":4.2,"temperature_c":58}
        )
        rules = CAUSE_RULES.get(defect_class, [])

        matched = []
        for rule in rules:
            if rule["condition"](state):
                matched.append({
                    "cause":      rule["cause"],
                    "action":     rule["action"],
                    "confidence": rule["confidence"]
                })

        if not matched:
            return {
                "cause":      "Unknown — no sensor correlation found",
                "action":     "Manual inspection required",
                "confidence": 0.0,
                "machine_state": state
            }

        # Return highest confidence cause
        best = max(matched, key=lambda x: x["confidence"])
        best["machine_state"] = state
        best["all_causes"]    = matched
        return best
    