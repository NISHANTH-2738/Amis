# tests/test_isolation_forest.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(__file__)
))

import requests

r    = requests.get(
    "http://localhost:8000/machines/anomaly-scan"
)
data = r.json()

print("ISOLATION FOREST — MACHINE ANOMALY SCAN")
print("=" * 55)
for m in data:
    sev = m["severity"].upper()
    mid = m["machine_id"]
    rec = m["recommendation"][:45]
    print(f"  {sev:8} | {mid} | {rec}")
    if m["violations"]:
        for v in m["violations"]:
            sensor    = v["sensor"]
            value     = v["value"]
            threshold = v["threshold"]
            print(f"           → {sensor}: "
                  f"{value} "
                  f"(threshold {threshold})")
print("=" * 55)