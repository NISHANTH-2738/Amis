# backend/services/database_service.py
import json
import redis
from backend.database.models import Inspection, Alert
from backend.database.connection import SessionLocal

# Connect to Redis running in Docker
r = redis.Redis(host="localhost", port=6379, db=0)

def save_inspection(result: dict):
    """Saves every inspection result to PostgreSQL."""
    db = SessionLocal()
    try:
        defect_class   = None
        confidence     = None
        bbox           = None
        severity_level = result["severity"]["level"]
        severity_name  = result["severity"]["name"]
        root_cause     = None
        action         = None

        if result["defects"]:
            d            = result["defects"][0]
            defect_class = d["class"]
            confidence   = d["confidence"]
            bbox         = d.get("bbox")

        if result["root_cause"]:
            root_cause = result["root_cause"]["cause"]
            action     = result["root_cause"]["action"]

        record = Inspection(
            inspection_id  = result["inspection_id"],
            machine_id     = result["machine_id"],
            status         = result["status"],
            defect_class   = defect_class,
            confidence     = confidence,
            severity_level = severity_level,
            severity_name  = severity_name,
            root_cause     = root_cause,
            action         = action,
            bbox           = bbox,
            inference_ms   = result["inference_ms"],
            model_source   = result["model_source"],
        )
        db.add(record)
        db.commit()
        return record.id

    except Exception as e:
        db.rollback()
        print(f"DB save error: {e}")
        return None
    finally:
        db.close()

def save_alert(result: dict):
    """Saves Level 2+ alerts to PostgreSQL."""
    if result["severity"]["level"] < 2:
        return

    db = SessionLocal()
    try:
        defect_class = result["defects"][0]["class"] if result.get("defects") else "sensor_anomaly"
        confidence = result["defects"][0]["confidence"] if result.get("defects") else result["anomaly"].get("score")
        alert = Alert(
            inspection_id = result["inspection_id"],
            machine_id    = result["machine_id"],
            alert_level   = result["severity"]["level"],
            alert_name    = result["severity"]["name"],
            defect_class  = defect_class,
            message       = (
                f"{result['severity']['action']} | "
                f"Cause: {result['root_cause']['cause']}"
                if result["root_cause"]
                else result["severity"]["action"]
            ),
        )
        db.add(alert)
        db.commit()
        
        # Push to Redis alert history for real-time dashboard
        alert_payload = {
            "type":        "alert",
            "level":       result["severity"]["level"],
            "level_name":  result["severity"]["name"],
            "machine_id":  result["machine_id"],
            "defect":      defect_class,
            "confidence":  confidence,
            "action":      result["severity"]["action"],
            "root_cause":  result["root_cause"]["cause"] if result["root_cause"] else None,
            "fix":         result["root_cause"]["action"] if result["root_cause"] else None,
            "inspection_id": result["inspection_id"],
            "timestamp":   result["timestamp"],
        }
        r.lpush("fabriguard:alert_history", json.dumps(alert_payload))
        r.ltrim("fabriguard:alert_history", 0, 49)

    except Exception as e:
        db.rollback()
        print(f"Alert save error: {e}")
    finally:
        db.close()

def get_todays_stats() -> dict:
    from datetime import date
    db = SessionLocal()
    try:
        all_inspections = db.query(Inspection).all()
        all_alerts      = db.query(Alert).all()
        today           = date.today()

        # Debug — print what timestamps look like
        for rec in all_inspections[:3]:
            print(f"  DEBUG timestamp: {rec.timestamp} "
                  f"type: {type(rec.timestamp)}")

        todays = []
        for rec in all_inspections:
            if rec.timestamp is None:
                continue
            # Handle both datetime and string timestamps
            if hasattr(rec.timestamp, 'date'):
                rec_date = rec.timestamp.date()
            else:
                from datetime import datetime
                rec_date = datetime.fromisoformat(
                    str(rec.timestamp)
                ).date()
            if rec_date == today:
                todays.append(rec)

        total   = len(todays)
        defects = len([r for r in todays
                       if r.status == "FAIL"])

        active_alerts = 0
        for a in all_alerts:
            if a.timestamp is None:
                continue
            if hasattr(a.timestamp, 'date'):
                a_date = a.timestamp.date()
            else:
                from datetime import datetime
                a_date = datetime.fromisoformat(
                    str(a.timestamp)
                ).date()
            if a_date == today and not a.acknowledged:
                active_alerts += 1

        return {
            "inspected_today": total,
            "defects_today":   defects,
            "active_alerts":   active_alerts,
            "defect_rate":     round(
                (defects / total * 100)
                if total > 0 else 0, 2
            )
        }
    finally:
        db.close()
