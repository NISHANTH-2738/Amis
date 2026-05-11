
# backend/services/notification_service.py
import redis
import json
from datetime import datetime

# Connect to Redis running in Docker
r = redis.Redis(host="localhost", port=6379, db=0)

# Channel names — dashboard subscribes to these
CHANNELS = {
    "inspection": "fabriguard:inspections",
    "alert":      "fabriguard:alerts",
    "machine":    "fabriguard:machines",
}

def publish_inspection(result: dict):
    """
    Publishes every inspection result to Redis.
    Dashboard receives this in real time via WebSocket.
    """
    payload = {
        "type":          "inspection",
        "inspection_id": result["inspection_id"],
        "timestamp":     result["timestamp"],
        "machine_id":    result["machine_id"],
        "status":        result["status"],
        "severity":      result["severity"]["name"],
        "defect":        result["defects"][0]["class"]
                         if result["defects"] else None,
        "inference_ms":  result["inference_ms"],
    }
    r.publish(
        CHANNELS["inspection"],
        json.dumps(payload)
    )

def publish_alert(result: dict):
    """
    Publishes alerts only for Level 2 and above.
    Inspector, supervisor, engineer get notified.
    """
    level = result["severity"]["level"]
    print(f"  → publish_alert called: level={level}")  # debug
    if level < 2:
        return

    # Determine who gets notified
    notify = []
    if level >= 2: notify.append("inspector")
    if level >= 3: notify.append("supervisor")
    if level >= 4: notify.append("engineer")

    payload = {
        "type":        "alert",
        "level":       level,
        "level_name":  result["severity"]["name"],
        "machine_id":  result["machine_id"],
        "defect":      result["defects"][0]["class"],
        "confidence":  result["defects"][0]["confidence"],
        "action":      result["severity"]["action"],
        "root_cause":  result["root_cause"]["cause"]
                       if result["root_cause"] else None,
        "fix":         result["root_cause"]["action"]
                       if result["root_cause"] else None,
        "notify":      notify,
        "timestamp":   result["timestamp"],
        "inspection_id": result["inspection_id"],
    }

    r.publish(
        CHANNELS["alert"],
        json.dumps(payload)
    )

    # Also store in Redis list — keeps last 50 alerts
    r.lpush("fabriguard:alert_history",
            json.dumps(payload))
    r.ltrim("fabriguard:alert_history", 0, 49)

def get_recent_alerts(count: int = 10) -> list:
    """Returns last N alerts from Redis."""
    raw = r.lrange("fabriguard:alert_history",
                   0, count - 1)
    return [json.loads(a) for a in raw]

def update_dashboard_stats(stats: dict):
    """Updates live dashboard numbers in Redis cache."""
    r.setex(
        "fabriguard:dashboard_stats",
        60,               # expires after 60 seconds
        json.dumps(stats)
    )

def get_dashboard_stats() -> dict:
    """Returns cached dashboard stats."""
    raw = r.get("fabriguard:dashboard_stats")
    if raw:
        return json.loads(raw)
    return {
        "inspected_today": 0,
        "defects_today":   0,
        "active_alerts":   0,
        "defect_rate":     0.0
    }
def save_alert(result: dict):
    if result["severity"]["level"] < 2:
        return

    db = SessionLocal()
    try:
        alert = Alert(
            inspection_id = result["inspection_id"],
            machine_id    = result["machine_id"],
            alert_level   = result["severity"]["level"],
            alert_name    = result["severity"]["name"],
            defect_class  = result["defects"][0]["class"],
            message       = (
                f"{result['severity']['action']} | "
                f"Cause: {result['root_cause']['cause']}"
                if result["root_cause"]
                else result["severity"]["action"]
            ),
        )
        db.add(alert)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Alert save error: {e}")
    finally:
        db.close()