# ai_core/inference/isolation_forest_detector.py

class IsolationForestDetector:
    def scan_all_machines(self, machine_states):
        # Mock implementation
        results = []
        for machine_id, state in machine_states.items():
            # Simple mock logic
            violations = []
            if state.get("vibration", 0) > 1.5:
                violations.append("High vibration")
            if state.get("tool_age_days", 0) > 7:
                violations.append("Tool aging")
            
            severity = "ok"
            if len(violations) > 1:
                severity = "critical"
            elif len(violations) > 0:
                severity = "warning"
            
            results.append({
                "machine_id": machine_id,
                "severity": severity,
                "violations": violations,
                "recommendation": "Check machine" if violations else "OK",
                "predict_defect": "potential" if severity != "ok" else "none",
                "timestamp": "2023-01-01T00:00:00"
            })
        return results

detector = IsolationForestDetector()