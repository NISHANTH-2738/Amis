# backend/api/simulator.py
import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
))

import time
import requests
from datetime import datetime

API_URL  = "http://localhost:8000/inspect"
INTERVAL = 2  # seconds between inspections

def run_simulator():
    print("=" * 50)
    print("  FABRIGUARD — PRODUCTION SIMULATOR")
    print("=" * 50)
    print(f"  Sending inspection every {INTERVAL}s")
    print(f"  API: {API_URL}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 50 + "\n")

    total   = 0
    defects = 0

    while True:
        try:
            r    = requests.post(API_URL, timeout=5)
            data = r.json()

            total += 1
            status = data["status"]
            sev    = data["severity"]["name"]
            mach   = data["machine_id"]
            defect = data["defects"][0]["class"] \
                     if data["defects"] else "-"
            cause  = data["root_cause"]["cause"] \
                     if data["root_cause"] else "-"

            if status == "FAIL":
                defects += 1

            rate = round((defects / total) * 100, 1)
            time_now = datetime.now().strftime("%H:%M:%S")

            # Colour coding in terminal
            badge = {
                "PASS":    "  PASS   ",
                "MONITOR": " MONITOR ",
                "ALERT":   "  ALERT  ",
                "ISOLATE": " ISOLATE ",
                "STOP":    "  STOP   ",
            }.get(sev, sev)

            print(
                f"[{time_now}] {badge} | "
                f"{mach} | {defect:15} | "
                f"rate: {rate}% | {cause[:40]}"
            )

        except requests.exceptions.ConnectionError:
            print("  Waiting for API to start...")
            print("  Run: python backend/api/main.py")

        except KeyboardInterrupt:
            print(f"\n  Simulator stopped.")
            print(f"  Total inspected: {total}")
            print(f"  Total defects:   {defects}")
            print(f"  Final rate:      {rate}%")
            break

        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(INTERVAL)

if __name__ == "__main__":
    run_simulator()