# backend/services/database_service.py

import json
from datetime import date, datetime

import redis

from backend.database.connection import SessionLocal

# IMPORTANT:
# Import models directly from models.py
from backend.database.models import (
    Inspection,
    Alert,
    MachineState,
)

# ---------------------------------------------
# Redis Connection
# ---------------------------------------------

try:
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True,
    )

    r.ping()

    print("Redis connected")

except Exception as e:
    print(f"Redis unavailable: {e}")

    r = None


# ---------------------------------------------
# Save Inspection
# ---------------------------------------------

def save_inspection(result: dict):
    """
    Save inspection result into database.
    """

    db = SessionLocal()

    try:
        defect_class = None
        confidence = None
        bbox = None

        severity_level = result["severity"]["level"]
        severity_name = result["severity"]["name"]

        root_cause = None
        action = None

        # -------------------------------------
        # Extract defect information
        # -------------------------------------

        if result.get("defects"):
            d = result["defects"][0]

            defect_class = d.get("class")

            confidence = d.get("confidence")

            bbox = d.get("bbox")

        # -------------------------------------
        # Extract root cause information
        # -------------------------------------

        if result.get("root_cause"):
            root_cause = result["root_cause"].get(
                "cause"
            )

            action = result["root_cause"].get(
                "action"
            )

        # -------------------------------------
        # Create DB Record
        # -------------------------------------

        record = Inspection(
            inspection_id=result["inspection_id"],
            machine_id=result["machine_id"],
            status=result["status"],
            defect_class=defect_class,
            confidence=confidence,
            severity_level=severity_level,
            severity_name=severity_name,
            root_cause=root_cause,
            action=action,
            bbox=bbox,
            inference_ms=result["inference_ms"],
            model_source=result["model_source"],
        )

        db.add(record)

        db.commit()

        db.refresh(record)

        return record.id

    except Exception as e:
        db.rollback()

        print(f"DB save error: {e}")

        return None

    finally:
        db.close()


# ---------------------------------------------
# Save Alert
# ---------------------------------------------

def save_alert(result: dict):
    """
    Save severity level 2+ alerts.
    """

    if result["severity"]["level"] < 2:
        return

    db = SessionLocal()

    try:
        defect_class = (
            result["defects"][0]["class"]
            if result.get("defects")
            else "sensor_anomaly"
        )

        confidence = (
            result["defects"][0]["confidence"]
            if result.get("defects")
            else result["anomaly"].get("score")
        )

        # -------------------------------------
        # Create Alert Record
        # -------------------------------------

        alert = Alert(
            inspection_id=result["inspection_id"],
            machine_id=result["machine_id"],
            alert_level=result["severity"]["level"],
            alert_name=result["severity"]["name"],
            defect_class=defect_class,
            message=(
                f"{result['severity']['action']} | "
                f"Cause: {result['root_cause']['cause']}"
                if result.get("root_cause")
                else result["severity"]["action"]
            ),
        )

        db.add(alert)

        db.commit()

        # -------------------------------------
        # Redis Realtime Alert Push
        # -------------------------------------

        if r:
            alert_payload = {
                "type": "alert",
                "level": result["severity"]["level"],
                "level_name": result["severity"]["name"],
                "machine_id": result["machine_id"],
                "defect": defect_class,
                "confidence": confidence,
                "action": result["severity"]["action"],
                "root_cause": (
                    result["root_cause"]["cause"]
                    if result.get("root_cause")
                    else None
                ),
                "fix": (
                    result["root_cause"]["action"]
                    if result.get("root_cause")
                    else None
                ),
                "inspection_id": result[
                    "inspection_id"
                ],
                "timestamp": result["timestamp"],
            }

            r.lpush(
                "fabriguard:alert_history",
                json.dumps(alert_payload),
            )

            r.ltrim(
                "fabriguard:alert_history",
                0,
                49,
            )

    except Exception as e:
        db.rollback()

        print(f"Alert save error: {e}")

    finally:
        db.close()


# ---------------------------------------------
# Dashboard Statistics
# ---------------------------------------------

def get_todays_stats() -> dict:
    """
    Dashboard statistics for today.
    """

    db = SessionLocal()

    try:
        all_inspections = db.query(
            Inspection
        ).all()

        all_alerts = db.query(Alert).all()

        today = date.today()

        # -------------------------------------
        # Today's inspections
        # -------------------------------------

        todays = []

        for rec in all_inspections:
            if rec.timestamp is None:
                continue

            if hasattr(rec.timestamp, "date"):
                rec_date = rec.timestamp.date()

            else:
                rec_date = datetime.fromisoformat(
                    str(rec.timestamp)
                ).date()

            if rec_date == today:
                todays.append(rec)

        # -------------------------------------
        # Counts
        # -------------------------------------

        total = len(todays)

        defects = len(
            [
                r
                for r in todays
                if r.status == "FAIL"
            ]
        )

        # -------------------------------------
        # Active Alerts
        # -------------------------------------

        active_alerts = 0

        for a in all_alerts:
            if a.timestamp is None:
                continue

            if hasattr(a.timestamp, "date"):
                a_date = a.timestamp.date()

            else:
                a_date = datetime.fromisoformat(
                    str(a.timestamp)
                ).date()

            if (
                a_date == today
                and not a.acknowledged
            ):
                active_alerts += 1

        # -------------------------------------
        # Final Stats
        # -------------------------------------

        return {
            "inspected_today": total,
            "defects_today": defects,
            "active_alerts": active_alerts,
            "defect_rate": round(
                (
                    defects / total * 100
                    if total > 0
                    else 0
                ),
                2,
            ),
        }

    finally:
        db.close()
