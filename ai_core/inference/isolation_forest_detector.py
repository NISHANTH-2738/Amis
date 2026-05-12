from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest


FEATURES = ["tool_age_days", "vibration", "tension_kn", "temperature_c"]
THRESHOLDS = {
    "tool_age_days": {"warning": 7, "label": "Tool nearing end of life"},
    "vibration": {"warning": 1.5, "label": "High vibration"},
    "tension_kn": {"warning": 4.5, "label": "High thread tension"},
    "temperature_c": {"warning": 63, "label": "Machine overheating"},
}


class IsolationForestDetector:
    def __init__(self, model_path: str = "ai_core/models/isolation_forest.pkl"):
        self.model_path = Path(model_path)
        self.model = None
        self._load_or_bootstrap()

    def _state_vector(self, state):
        return np.asarray([[float(state.get(feature, 0.0)) for feature in FEATURES]])

    def _load_or_bootstrap(self):
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            return
        rng = np.random.default_rng(42)
        normal = np.column_stack(
            [
                rng.normal(3.5, 1.0, 500),
                rng.normal(1.0, 0.2, 500),
                rng.normal(4.2, 0.15, 500),
                rng.normal(58.0, 2.0, 500),
            ]
        )
        self.model = IsolationForest(contamination=0.08, random_state=42)
        self.model.fit(normal)

    def save(self):
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, self.model_path)

    def train_normal(self, states):
        vectors = np.vstack([self._state_vector(state) for state in states])
        self.model = IsolationForest(contamination=0.08, random_state=42)
        self.model.fit(vectors)
        self.save()

    def check_machine(self, machine_id, state):
        vector = self._state_vector(state)
        raw_score = float(self.model.decision_function(vector)[0])
        prediction = int(self.model.predict(vector)[0])
        violations = []
        for sensor, config in THRESHOLDS.items():
            value = float(state.get(sensor, 0.0))
            threshold = float(config["warning"])
            if value > threshold:
                violations.append(
                    {
                        "sensor": sensor,
                        "value": value,
                        "threshold": threshold,
                        "warning": config["label"],
                    }
                )

        is_anomaly = prediction == -1 or bool(violations)
        severity = "critical" if len(violations) >= 2 else "warning" if is_anomaly else "ok"
        return {
            "machine_id": machine_id,
            "score": round(raw_score, 4),
            "is_anomaly": is_anomaly,
            "model": "isolation_forest",
            "severity": severity,
            "violations": violations,
            "recommendation": "Inspect machine and verify tool/tension settings" if is_anomaly else "OK",
            "predict_defect": "potential" if is_anomaly else "none",
            "timestamp": datetime.now().isoformat(),
        }

    def scan_all_machines(self, machine_states):
        return [self.check_machine(machine_id, state) for machine_id, state in machine_states.items()]


detector = IsolationForestDetector()
