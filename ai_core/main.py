# backend/api/main.py

import sys, os
sys.path.append(os.path.dirname(
    os.path.dirname(os.path.dirname(__file__))
))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json, uuid
from datetime import datetime

from backend.services.inspection_pipeline  import run_inspection
from backend.services.database_service     import (
    get_todays_stats, save_inspection, save_alert
)
from backend.services.notification_service import (
    get_recent_alerts, get_dashboard_stats
)
from backend.database.connection           import (
    create_tables, SessionLocal
)
from backend.database.models               import (
    Inspection, Alert
)
#from ai_core.inference.isolation_forest_detector import detector
#from ai_core.inference.patchcore_detector        import patchcore
from ai_core.inference.mock_detector import *

# ── APP SETUP ────────────────────────────────────────
app = FastAPI(
    title="FabriGuard API",
    description="AI-Powered Knitwear Defect Detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WEBSOCKET MANAGER ────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        print(f"Dashboard connected. Total: {len(self.active)}")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        print(f"Dashboard disconnected. Total: {len(self.active)}")

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            if ws in self.active:
                self.active.remove(ws)

manager = ConnectionManager()

# ── STARTUP ──────────────────────────────────────────
@app.on_event("startup")
async def startup():
    create_tables()
    print("✅ FabriGuard API started")
    print("📊 Docs: http://localhost:8000/docs")

# ── HEALTH CHECK ─────────────────────────────────────
@app.get("/")
async def root():
    return {
        "system":  "FabriGuard",
        "status":  "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {
        "status":    "ok",
        "timestamp": datetime.now().isoformat()
    }

# ── CORE INSPECTION ENDPOINT ─────────────────────────
@app.post("/inspect")
async def inspect(file: UploadFile = File(None)):
    """
    Main inspection endpoint.
    Accepts an image file (optional — mock ignores it).
    Runs full pipeline: detect → severity → root cause
    → save → alert → broadcast to dashboard.
    """
    image_path = None

    if file:
        os.makedirs("uploads", exist_ok=True)
        image_path = f"uploads/{uuid.uuid4()}_{file.filename}"
        with open(image_path, "wb") as f:
            f.write(await file.read())

    result = run_inspection(image_path)

    # Broadcast inspection to dashboard
    await manager.broadcast({
        "type":           "inspection",
        "inspection_id":  result["inspection_id"],
        "timestamp":      result["timestamp"],
        "machine_id":     result["machine_id"],
        "status":         result["status"],
        "severity":       result["severity"]["name"],
        "severity_level": result["severity"]["level"],
        "defect":         result["defects"][0]["class"]
                          if result["defects"] else None,
        "confidence":     result["defects"][0]["confidence"]
                          if result["defects"] else None,
        "action":         result["severity"]["action"],
        "root_cause":     result["root_cause"]["cause"]
                          if result["root_cause"] else None,
        "fix":            result["root_cause"]["action"]
                          if result["root_cause"] else None,
        "inference_ms":   result["inference_ms"],
    })

    # Fire alert broadcast for level 2+
    if result["severity"]["level"] >= 2:
        await manager.broadcast({
            "type":       "alert",
            "level":      result["severity"]["level"],
            "level_name": result["severity"]["name"],
            "machine_id": result["machine_id"],
            "defect":     result["defects"][0]["class"],
            "action":     result["severity"]["action"],
            "cause":      result["root_cause"]["cause"]
                          if result["root_cause"] else None,
        })

    return result

# ── WEBCAM INSPECTION ─────────────────────────────────
@app.post("/inspect/webcam")
async def inspect_webcam(image_data: str = None):
    """
    Receives base64 image from browser webcam.
    Processes and returns defect detection.
    """
    if not image_data:
        return {"error": "No image data"}

    try:
        import base64
        import io
        from PIL import Image

        img_bytes = base64.b64decode(
            image_data.split(',')[1]
        )
        img = Image.open(io.BytesIO(img_bytes))

        os.makedirs("uploads/webcam", exist_ok=True)
        temp_path = f"uploads/webcam/{uuid.uuid4()}.jpg"
        img.save(temp_path)

        result = run_inspection(temp_path)

        await manager.broadcast({
            "type":           "inspection",
            "inspection_id":  result["inspection_id"],
            "timestamp":      result["timestamp"],
            "machine_id":     result["machine_id"],
            "status":         result["status"],
            "severity":       result["severity"]["name"],
            "severity_level": result["severity"]["level"],
            "defect":         result["defects"][0]["class"]
                              if result["defects"] else None,
            "confidence":     result["defects"][0]["confidence"]
                              if result["defects"] else None,
            "source":         result["model_source"],
        })

        return result

    except Exception as e:
        return {"error": str(e)}

# ── DASHBOARD STATS ───────────────────────────────────
@app.get("/dashboard/stats")
async def dashboard_stats():
    """Returns today's live stats for supervisor dashboard."""
    return get_todays_stats()

# ── RECENT ALERTS ─────────────────────────────────────
@app.get("/alerts/recent")
async def recent_alerts(count: int = 10):
    """Returns last N alerts from Redis."""
    return get_recent_alerts(count)

# ── RECENT INSPECTIONS ────────────────────────────────
@app.get("/inspections/recent")
async def recent_inspections(count: int = 20):
    """Returns last N inspection records from PostgreSQL."""
    db = SessionLocal()
    try:
        records = db.query(Inspection)\
                    .order_by(Inspection.id.desc())\
                    .limit(count).all()
        return [{
            "inspection_id":  r.inspection_id,
            "timestamp":      r.timestamp.isoformat()
                              if r.timestamp else None,
            "machine_id":     r.machine_id,
            "status":         r.status,
            "defect_class":   r.defect_class,
            "confidence":     r.confidence,
            "severity_level": r.severity_level,
            "severity_name":  r.severity_name,
            "root_cause":     r.root_cause,
            "action":         r.action,
            "inference_ms":   r.inference_ms,
            "overridden":     r.overridden,
        } for r in records]
    finally:
        db.close()

# ── INSPECTOR OVERRIDE ────────────────────────────────
@app.post("/inspect/{inspection_id}/override")
async def override_inspection(
    inspection_id: str,
    override_note: str = "Inspector override"
):
    """
    Inspector disagrees with AI decision.
    Marks record as overridden — feeds back to model later.
    """
    db = SessionLocal()
    try:
        record = db.query(Inspection).filter(
            Inspection.inspection_id == inspection_id
        ).first()

        if not record:
            return JSONResponse(
                status_code=404,
                content={"error": "Inspection not found"}
            )

        record.overridden    = True
        record.override_note = override_note
        db.commit()

        await manager.broadcast({
            "type":          "override",
            "inspection_id": inspection_id,
            "note":          override_note,
        })

        return {
            "status":        "overridden",
            "inspection_id": inspection_id,
            "note":          override_note
        }
    finally:
        db.close()

# ── ACKNOWLEDGE ALERT ─────────────────────────────────
@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int):
    """Supervisor acknowledges alert — removes from active count."""
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(
            Alert.id == alert_id
        ).first()
        if not alert:
            return JSONResponse(
                status_code=404,
                content={"error": "Alert not found"}
            )
        alert.acknowledged = True
        db.commit()
        return {
            "status":   "acknowledged",
            "alert_id": alert_id
        }
    finally:
        db.close()

# ── MACHINE STATUS ────────────────────────────────────
@app.get("/machines/status")
async def machine_status():
    """Returns current simulated machine sensor states."""
    from backend.services.root_cause_engine import MOCK_MACHINE_STATE
    machines = []
    for machine_id, state in MOCK_MACHINE_STATE.items():
        health = "ok"
        if state["tool_age_days"] > 7:  health = "critical"
        elif state["vibration"] > 1.5:  health = "warning"
        elif state["tension_kn"] > 4.5: health = "warning"
        machines.append({
            "machine_id":    machine_id,
            "health":        health,
            "tool_age_days": state["tool_age_days"],
            "vibration":     state["vibration"],
            "tension_kn":    state["tension_kn"],
            "temperature_c": state["temperature_c"],
        })
    return machines

# ── ISOLATION FOREST — ANOMALY SCAN ──────────────────
@app.get("/machines/anomaly-scan")
async def anomaly_scan():
    """
    Scans all machines using Isolation Forest.
    Returns anomaly assessment for each machine.
    Fires predictive warning before defects appear.
    """
    try:
        from backend.services.root_cause_engine import (
            MOCK_MACHINE_STATE
        )
        results = detector.scan_all_machines(
            MOCK_MACHINE_STATE
        )

        for r in results:
            if r["severity"] in ["critical", "warning"]:
                await manager.broadcast({
                    "type":           "sensor_anomaly",
                    "machine_id":     r["machine_id"],
                    "severity":       r["severity"],
                    "violations":     r["violations"],
                    "recommendation": r["recommendation"],
                    "predict_defect": r["predict_defect"],
                    "timestamp":      r["timestamp"],
                })

        return json.loads(json.dumps(results, default=str))

    except Exception as e:
        return {"error": str(e)}

# ── PATCHCORE — PRODUCT SETUP ─────────────────────────
@app.post("/patchcore/setup")
async def patchcore_setup(
    product_name: str,
    files: list[UploadFile] = File(...)
):
    """
    Engineer uploads good product photos.
    PatchCore builds memory bank instantly.
    New product ready in minutes — zero training needed.
    """
    os.makedirs("uploads/reference", exist_ok=True)
    saved_paths = []

    for file in files:
        safe_name = file.filename.replace(" ", "_")
        path = f"uploads/reference/{product_name}_{safe_name}"
        with open(path, "wb") as f:
            f.write(await file.read())
        saved_paths.append(path)

    result = patchcore.setup_product(
        product_name, saved_paths
    )

    await manager.broadcast({
        "type":         "product_onboarded",
        "product_name": product_name,
        "images_used":  result.get("images_used", 0),
        "status":       result.get("status", "ready"),
        "timestamp":    datetime.now().isoformat(),
    })

    return result

# ── PATCHCORE — STATUS ────────────────────────────────
@app.get("/patchcore/status")
async def patchcore_status():
    """Returns current PatchCore product profile status."""
    return patchcore.get_status()

# ── PATCHCORE — INSPECT ───────────────────────────────
@app.post("/patchcore/inspect")
async def patchcore_inspect(
    file: UploadFile = File(...)
):
    """
    Inspect image using PatchCore memory bank.
    No training needed — zero-shot for new products.
    """
    os.makedirs("uploads/inspect", exist_ok=True)
    safe_name = file.filename.replace(" ", "_")
    path      = f"uploads/inspect/{uuid.uuid4()}_{safe_name}"

    with open(path, "wb") as f:
        f.write(await file.read())

    from backend.services.severity_engine import SeverityEngine
    sev_engine = SeverityEngine()

    detection = patchcore.inspect(path)
    severity  = sev_engine.classify(detection)

    await manager.broadcast({
        "type":           "inspection",
        "inspection_id":  str(uuid.uuid4())[:8],
        "timestamp":      datetime.now().isoformat(),
        "machine_id":     "PATCHCORE",
        "status":         detection["status"],
        "severity":       severity["name"],
        "severity_level": severity["level"],
        "defect":         "anomaly"
                          if detection["status"] == "FAIL"
                          else None,
        "confidence":     detection["defects"][0]["confidence"]
                          if detection["defects"] else None,
        "action":         severity["action"],
        "source":         "patchcore",
    })

    return {
        "detection": detection,
        "severity":  severity,
        "source":    "patchcore",
        "product":   patchcore.product_name,
    }

# ── WEBSOCKET ENDPOINT ────────────────────────────────
@app.websocket("/ws/dashboard")
async def websocket_dashboard(ws: WebSocket):
    """
    Dashboard connects here for live updates.
    Receives every inspection and alert in real time.
    """
    await manager.connect(ws)
    try:
        stats = get_todays_stats()
        await ws.send_json({
            "type":  "stats",
            "stats": stats
        })
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ── RUN SERVER ────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
