MOCK_MACHINE_STATE = {
    "M-01": {"tool_age_days": 3, "vibration": 1.0, "tension_kn": 4.2, "temperature_c": 58},
    "M-02": {"tool_age_days": 5, "vibration": 2.1, "tension_kn": 4.6, "temperature_c": 61},
    "M-03": {"tool_age_days": 1, "vibration": 0.9, "tension_kn": 4.1, "temperature_c": 57},
    "M-04": {"tool_age_days": 8, "vibration": 1.8, "tension_kn": 4.9, "temperature_c": 65},
    "M-05": {"tool_age_days": 2, "vibration": 1.0, "tension_kn": 4.2, "temperature_c": 58},
    "M-06": {"tool_age_days": 4, "vibration": 1.1, "tension_kn": 4.3, "temperature_c": 59},
}

CAUSE_RULES = {
    "needle_line": [
        {
            "condition": lambda s: s["tool_age_days"] > 7,
            "cause": "Needle overdue for replacement",
            "action": "Replace needle immediately",
            "confidence": 0.91,
        },
        {
            "condition": lambda s: s["vibration"] > 1.5,
            "cause": "Excessive machine vibration bending needle",
            "action": "Inspect and tighten machine mounts",
            "confidence": 0.78,
        },
    ],
    "drop_stitch": [
        {
            "condition": lambda s: s["tension_kn"] > 4.5,
            "cause": "Warp tension too high; thread skipping",
            "action": "Reduce tension to 4.2 kN baseline",
            "confidence": 0.85,
        },
        {
            "condition": lambda s: s["temperature_c"] > 63,
            "cause": "Motor overheating affecting timing",
            "action": "Check cooling fan and rest machine for 10 minutes",
            "confidence": 0.72,
        },
    ],
    "hole": [
        {
            "condition": lambda s: s["tool_age_days"] > 6,
            "cause": "Worn needle tip causing thread breaks",
            "action": "Replace needle and inspect thread path",
            "confidence": 0.88,
        },
        {
            "condition": lambda s: s["vibration"] > 1.8,
            "cause": "High vibration causing misalignment",
            "action": "Balance machine and check bearings",
            "confidence": 0.76,
        },
    ],
    "run_ladder": [
        {
            "condition": lambda s: s["tension_kn"] > 4.4,
            "cause": "Excess tension causing chain stitch failure",
            "action": "Recalibrate tension to 4.1-4.3 kN",
            "confidence": 0.83,
        }
    ],
    "stain": [
        {
            "condition": lambda s: s["tool_age_days"] > 5,
            "cause": "Worn parts causing oil leakage onto fabric",
            "action": "Inspect oil seals and clean fabric path",
            "confidence": 0.79,
        }
    ],
    "unknown_anomaly": [
        {
            "condition": lambda s: s["vibration"] > 1.5 or s["temperature_c"] > 63,
            "cause": "Unknown visual anomaly correlated with unstable machine state",
            "action": "Inspect machine state and review product sample manually",
            "confidence": 0.66,
        }
    ],
}

DEFAULT_CAUSES = {
    "hole": {
        "cause": "Needle damage or yarn break at stitch formation",
        "operator_action": "Stop affected roll, mark defect zone, inspect needle path",
        "maintenance_action": "Replace needle and check yarn guide alignment",
    },
    "stain": {
        "cause": "Oil leakage or contaminated fabric path",
        "operator_action": "Segregate stained material and clean contact rollers",
        "maintenance_action": "Inspect oil seals, lubrication points, and drip guards",
    },
    "needle_line": {
        "cause": "Bent or worn needle creating repeated line defect",
        "operator_action": "Pause line and inspect needle bed section",
        "maintenance_action": "Replace worn needle and verify machine vibration",
    },
    "drop_stitch": {
        "cause": "Yarn tension instability or missed stitch formation",
        "operator_action": "Review affected fabric and reduce line speed",
        "maintenance_action": "Recalibrate yarn tension and inspect feeders",
    },
    "run_ladder": {
        "cause": "Chain stitch failure caused by tension spike",
        "operator_action": "Isolate fabric roll and inspect recent output",
        "maintenance_action": "Adjust tension and inspect take-down rollers",
    },
    "pilling": {
        "cause": "Surface abrasion or yarn quality variation",
        "operator_action": "Flag roll for quality review",
        "maintenance_action": "Check fabric handling path for abrasion points",
    },
    "unknown_anomaly": {
        "cause": "Unclassified visual anomaly",
        "operator_action": "Manual quality inspection required",
        "maintenance_action": "Review machine state and sample image",
    },
}


class RootCauseEngine:
    def analyse(self, defect_class: str, machine_id: str, sensor_state: dict | None = None) -> dict:
        state = sensor_state or MOCK_MACHINE_STATE.get(
            machine_id,
            {"tool_age_days": 0, "vibration": 1.0, "tension_kn": 4.2, "temperature_c": 58},
        )
        default = DEFAULT_CAUSES.get(defect_class, DEFAULT_CAUSES["unknown_anomaly"])
        matched = []
        for rule in CAUSE_RULES.get(defect_class, []):
            if rule["condition"](state):
                matched.append(
                    {
                        "cause": rule["cause"],
                        "action": rule["action"],
                        "operator_action": default["operator_action"],
                        "maintenance_action": rule["action"],
                        "confidence": rule["confidence"],
                    }
                )

        if not matched:
            return {
                "cause": default["cause"],
                "action": default["operator_action"],
                "operator_action": default["operator_action"],
                "maintenance_action": default["maintenance_action"],
                "confidence": 0.0,
                "machine_id": machine_id,
                "machine_state": state,
                "all_causes": [],
            }

        best = max(matched, key=lambda item: item["confidence"])
        best["machine_id"] = machine_id
        best["machine_state"] = state
        best["all_causes"] = matched
        return best
