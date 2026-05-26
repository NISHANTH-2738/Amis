from __future__ import annotations

import json
import os
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from backend.api.websocket.manager import dashboard_manager
from backend.database.connection import SessionLocal
from backend.database.models import Alert, Inspection
from backend.detector.engine import ModelUnavailableError, engine
from backend.services.database_service import get_todays_stats
from backend.services.notification_service import get_recent_alerts


router = APIRouter()
METRICS_PATH = "ai_core/models/fabriguard_v1/metrics_report.json"


@router.get("/dashboard/stats")
async def dashboard_stats():
    return get_todays_stats()


@router.get("/export/csv")
async def export_csv():
    csv_path = "logs/defect_log.csv"
    if not os.path.exists(csv_path):
        return JSONResponse(
            status_code=404,
            content={"error": "No log file yet. Run inspections first."},
        )
    return FileResponse(
        path=csv_path,
        filename=f"industrial_defect_log_{datetime.now().strftime('%Y%m%d')}.csv",
        media_type="text/csv",
    )


@router.get("/alerts/recent")
async def recent_alerts(count: int = 10):
    return get_recent_alerts(count)


@router.get("/inspections/recent")
async def recent_inspections(count: int = 20):
    db = SessionLocal()
    try:
        records = (
            db.query(Inspection)
            .order_by(Inspection.id.desc())
            .limit(count)
            .all()
        )
        return [
            {
                "inspection_id": record.inspection_id,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                "machine_id": record.machine_id,
                "status": record.status,
                "defect_class": record.defect_class,
                "defects": [
                    {
                        "class": record.defect_class,
                        "confidence": record.confidence,
                        "bbox": record.bbox,
                    }
                ]
                if record.defect_class
                else [],
                "confidence": record.confidence,
                "bbox": record.bbox,
                "severity": {
                    "name": record.severity_name,
                    "level": record.severity_level,
                    "score": record.confidence or 0,
                },
                "severity_level": record.severity_level,
                "severity_name": record.severity_name,
                "root_cause": record.root_cause,
                "action": record.action,
                "inference_ms": record.inference_ms,
                "model_source": record.model_source,
                "overridden": record.overridden,
            }
            for record in records
        ]
    finally:
        db.close()


@router.post("/inspect/{inspection_id}/override")
async def override_inspection(
    inspection_id: str,
    override_note: str = "Inspector override",
):
    db = SessionLocal()
    try:
        record = (
            db.query(Inspection)
            .filter(Inspection.inspection_id == inspection_id)
            .first()
        )

        if not record:
            return JSONResponse(
                status_code=404,
                content={"error": "Inspection not found"},
            )

        record.overridden = True
        record.override_note = override_note
        db.commit()

        await dashboard_manager.broadcast(
            {
                "type": "override",
                "payload": {
                    "inspection_id": inspection_id,
                    "note": override_note,
                },
            }
        )

        return {
            "status": "overridden",
            "inspection_id": inspection_id,
            "note": override_note,
        }
    finally:
        db.close()


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return JSONResponse(
                status_code=404,
                content={"error": "Alert not found"},
            )
        alert.acknowledged = True
        db.commit()
        return {"status": "acknowledged", "alert_id": alert_id}
    finally:
        db.close()


@router.get("/machines/status")
async def machine_status():
    from backend.services.root_cause_engine import MOCK_MACHINE_STATE

    machines = []
    for machine_id, state in MOCK_MACHINE_STATE.items():
        health = "ok"
        if state["tool_age_days"] > 7:
            health = "critical"
        elif state["vibration"] > 1.5 or state["tension_kn"] > 4.5:
            health = "warning"
        machines.append(
            {
                "machine_id": machine_id,
                "health": health,
                "tool_age_days": state["tool_age_days"],
                "vibration": state["vibration"],
                "tension_kn": state["tension_kn"],
                "temperature_c": state["temperature_c"],
            }
        )
    return machines


@router.get("/machines/anomaly-scan")
async def anomaly_scan():
    from ai_core.inference.isolation_forest_detector import detector
    from backend.services.root_cause_engine import MOCK_MACHINE_STATE

    results = detector.scan_all_machines(MOCK_MACHINE_STATE)
    for result in results:
        if result["severity"] in ["critical", "warning"]:
            await dashboard_manager.broadcast(
                {
                    "type": "sensor_anomaly",
                    "payload": {
                        **result,
                        "timestamp": result.get("timestamp")
                        or datetime.now().isoformat(),
                    },
                }
            )
    return json.loads(json.dumps(results, default=str))


@router.get("/model/status")
async def get_model_status():
    return engine.status()


@router.post("/model/reload")
async def post_model_reload():
    try:
        engine.load(force=True)
        return engine.status() | {"reloaded": True}
    except ModelUnavailableError as exc:
        return JSONResponse(
            status_code=503,
            content=engine.status() | {"reloaded": False, "error": str(exc)},
        )


@router.get("/model/metrics")
async def get_model_metrics():
    if not os.path.exists(METRICS_PATH):
        return {
            "available": False,
            "path": METRICS_PATH,
            "message": "Train/export YOLOv8 first to generate metrics_report.json",
        }
    with open(METRICS_PATH, "r", encoding="utf-8") as file:
        metrics = json.load(file)
    metrics["available"] = True
    return metrics
