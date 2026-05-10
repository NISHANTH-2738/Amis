# ai_core/inference/isolation_forest_detector.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
))

import numpy as np
import json
import random
from datetime import datetime
from sklearn.ensemble import IsolationForest

# ── NORMAL OPERATING RANGES ──────────────────────────
# These represent healthy machine sensor readings.
# Isolation Forest learns this as "normal".

NORMAL_RANGES = {
    "tool_age_days": (0, 6),
    "vibration":     (0.8, 1.3),
    "tension_kn":    (4.0, 4.4),
    "temperature_c": (55, 62),
}

# ── SENSOR FEATURE NAMES ─────────────────────────────
FEATURES = [
    "tool_age_days",
    "vibration",
    "tension_kn",
    "temperature_c"
]

# ── ANOMALY THRESHOLDS ───────────────────────────────
ANOMALY_ACTIONS = {
    "tool_age_days": {
        "threshold": 7,
        "warning":   "Tool nearing end of life",
        "action":    "Schedule replacement within 1 shift"
    },
    "vibration": {
        "threshold": 1.5,
        "warning":   "Abnormal machine vibration detected",
        "action":    "Inspect bearings and machine mounts"
    },
    "tension_kn": {
        "threshold": 4.5,
        "warning":   "Warp tension exceeding safe range",
        "action":    "Recalibrate tension to 4.1-4.3 kN"
    },
    "temperature_c": {
        "threshold": 63,
        "warning":   "Motor temperature above normal",
        "action":    "Check cooling fan. Rest machine 10 min."
    },
}


class IsolationForestDetector:
    """
    Monitors machine sensor streams.
    Detects abnormal operating conditions.
    Fires warning BEFORE defects appear on product.

    Works on any machine — no defect labels needed.
    Just needs normal operation data to train on.
    """

    def __init__(self, contamination: float = 0.05):
        self.model        = IsolationForest(
            n_estimators  = 100,
            contamination = contamination,
            random_state  = 42
        )
        self.is_trained   = False
        self.feature_names = FEATURES

    def generate_normal_data(self,
                             n_samples: int = 500) -> np.ndarray:
        """
        Generates synthetic normal sensor readings
        for training. In production this would come
        from real historical IIoT sensor data.
        """
        data = []
        for _ in range(n_samples):
            sample = [
                random.uniform(*NORMAL_RANGES["tool_age_days"]),
                random.uniform(*NORMAL_RANGES["vibration"]),
                random.uniform(*NORMAL_RANGES["tension_kn"]),
                random.uniform(*NORMAL_RANGES["temperature_c"]),
            ]
            data.append(sample)
        return np.array(data)

    def train(self, sensor_data: np.ndarray = None):
        """
        Train on normal machine operation data.
        Learns what healthy operation looks like.
        Anything outside this = anomaly.
        """
        if sensor_data is None:
            sensor_data = self.generate_normal_data(500)

        self.model.fit(sensor_data)
        self.is_trained = True
        print(f"✅ Isolation Forest trained on "
              f"{len(sensor_data)} normal samples")
        return self

    def check_machine(self, machine_id: str,
                      sensor_reading: dict) -> dict:
        """
        Check one machine's current sensor state.
        Returns anomaly assessment with specific warnings.

        sensor_reading: {
            tool_age_days, vibration,
            tension_kn, temperature_c
        }
        """
        if not self.is_trained:
            self.train()

        # Convert to feature vector
        features = np.array([[
            sensor_reading.get("tool_age_days", 0),
            sensor_reading.get("vibration",     1.0),
            sensor_reading.get("tension_kn",    4.2),
            sensor_reading.get("temperature_c", 58),
        ]])

        # Get anomaly score (-1 = anomaly, 1 = normal)
        prediction    = self.model.predict(features)[0]
        anomaly_score = self.model.score_samples(features)[0]
        is_anomaly    = prediction == -1

        # Identify specific sensor violations
        violations = []
        for feature, thresholds in ANOMALY_ACTIONS.items():
            value = sensor_reading.get(feature, 0)
            if value > thresholds["threshold"]:
                violations.append({
                    "sensor":    feature,
                    "value":     value,
                    "threshold": thresholds["threshold"],
                    "warning":   thresholds["warning"],
                    "action":    thresholds["action"],
                    "excess":    round(
                        value - thresholds["threshold"], 2
                    )
                })

        # Determine severity
        if not is_anomaly and not violations:
            severity = "normal"
        elif violations and max(
            v["excess"] for v in violations
        ) > 2:
            severity = "critical"
        elif is_anomaly or violations:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "machine_id":    machine_id,
            "timestamp":     datetime.now().isoformat(),
            "is_anomaly":    is_anomaly,
            "anomaly_score": round(float(anomaly_score), 4),
            "severity":      severity,
            "violations":    violations,
            "sensor_reading":sensor_reading,
            "recommendation": violations[0]["action"]
                              if violations
                              else "Continue normal operation",
            "predict_defect": is_anomaly or len(violations) > 0
        }

    def scan_all_machines(self,
                          machine_states: dict) -> list:
        """
        Scan all machines at once.
        Returns list of anomaly results sorted
        by severity — critical first.
        """
        results = []
        for machine_id, state in machine_states.items():
            result = self.check_machine(machine_id, state)
            results.append(result)

        # Sort: critical first, then warning, then normal
        order = {"critical": 0, "warning": 1, "normal": 2}
        results.sort(
            key=lambda x: order.get(x["severity"], 3)
        )
        return results


# ── SINGLETON INSTANCE ────────────────────────────────
# Import this in other files — already trained on import
detector = IsolationForestDetector()
detector.train()