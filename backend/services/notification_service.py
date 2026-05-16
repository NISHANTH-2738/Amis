"""Redis notification helpers for realtime dashboard compatibility.

FastAPI websockets are the primary live path. Redis is optional here: when it
is unavailable on a low-resource laptop, the inspection pipeline continues and
the API websocket manager still broadcasts events to connected dashboards.
"""

from __future__ import annotations

import json

import redis

from backend.database.connection import SessionLocal
from backend.database.models import Alert


try:
    r = redis.Redis(
        host="localhost",
        port=6379,
        db=0,
        decode_responses=True,
        socket_connect_timeout=0.25,
        socket_timeout=0.25,
    )
    r.ping()
except Exception as exc:
    print(f"Redis notifications unavailable: {exc}")
    r = None


CHANNELS = {
    "inspection": "fabriguard:inspections",
    "alert": "fabriguard:alerts",
    "machine": "fabriguard:machines",
}


def publish_inspection(result: dict) -> None:
    if not r:
        return
    defect = result["defects"][0] if result.get("defects") else None
    payload = {
        "type": "inspection",
        "inspection_id": result["inspection_id"],
        "timestamp": result["timestamp"],
        "machine_id": result["machine_id"],
        "status": result["status"],
        "severity": result["severity"]["name"],
        "severity_level": result["severity"]["level"],
        "defects": result.get("defects", []),
        "defect": defect.get("class") if defect else None,
        "confidence": defect.get("confidence") if defect else None,
        "bbox": defect.get("bbox") if defect else None,
        "inference_ms": result["inference_ms"],
    }
    r.publish(CHANNELS["inspection"], json.dumps(payload))


def publish_alert(result: dict) -> None:
    if not r or result["severity"]["level"] < 2:
        return
    defect = result["defects"][0] if result.get("defects") else None
    payload = {
        "type": "alert",
        "level": result["severity"]["level"],
        "level_name": result["severity"]["name"],
        "machine_id": result["machine_id"],
        "defect": defect.get("class") if defect else "sensor_anomaly",
        "confidence": defect.get("confidence") if defect else result.get("anomaly", {}).get("score"),
        "action": result["severity"]["action"],
        "root_cause": result["root_cause"]["cause"] if result.get("root_cause") else None,
        "fix": result["root_cause"]["action"] if result.get("root_cause") else None,
        "timestamp": result["timestamp"],
        "inspection_id": result["inspection_id"],
    }
    r.publish(CHANNELS["alert"], json.dumps(payload))
    r.lpush("fabriguard:alert_history", json.dumps(payload))
    r.ltrim("fabriguard:alert_history", 0, 49)


def get_recent_alerts(count: int = 10) -> list:
    if not r:
        db = SessionLocal()
        try:
            records = db.query(Alert).order_by(Alert.id.desc()).limit(count).all()
            return [
                {
                    "id": record.id,
                    "inspection_id": record.inspection_id,
                    "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                    "machine_id": record.machine_id,
                    "level": record.alert_level,
                    "level_name": record.alert_name,
                    "defect": record.defect_class,
                    "message": record.message,
                    "acknowledged": record.acknowledged,
                }
                for record in records
            ]
        finally:
            db.close()
    raw = r.lrange("fabriguard:alert_history", 0, count - 1)
    return [json.loads(item) for item in raw]


def update_dashboard_stats(stats: dict) -> None:
    if r:
        r.setex("fabriguard:dashboard_stats", 60, json.dumps(stats))


def get_dashboard_stats() -> dict:
    fallback = {
        "inspected_today": 0,
        "defects_today": 0,
        "active_alerts": 0,
        "defect_rate": 0.0,
    }
    if not r:
        return fallback
    raw = r.get("fabriguard:dashboard_stats")
    return json.loads(raw) if raw else fallback
