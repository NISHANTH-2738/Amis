# FabriGuard Project Summary

Generated: 2026-05-17, Asia/Calcutta

## Current Runtime Status

- Frontend dev server was stopped.
- Backend FastAPI server was stopped.
- Ports verified closed:
  - `3000` frontend
  - `8000` backend

## Project Purpose

FabriGuard is an AI-powered industrial fabric defect inspection platform. It is designed for a low-resource factory computer with Intel i3 CPU, 4 GB RAM, and no dedicated GPU. The system avoids local GPU inference and uses hosted Roboflow workflow inference for image analysis.

## Final Inspection Flow

```text
Frontend image upload
-> POST /inspect-image
-> backend/services/roboflow_service.py
-> hosted Roboflow workflow
-> backend/services/hybrid_detector.py
-> backend/services/severity_engine.py
-> backend/services/root_cause_engine.py
-> backend/services/inspection_pipeline.py
-> backend/services/database_service.py
-> backend/services/notification_service.py
-> WebSocket /ws/dashboard
-> frontend realtime dashboard
```

## Backend Modules

### `backend/api/main.py`

FastAPI application entrypoint.

Important routes:

- `GET /health`
- `POST /inspect-image`
- `POST /inspect/frame`
- `GET /inspections/recent`
- `GET /alerts/recent`
- `GET /machines/status`
- `GET /model/status`
- `WebSocket /ws/dashboard`

The `/inspect-image` route accepts a file upload, saves it temporarily, runs the full inspection pipeline, returns structured output, and broadcasts realtime events.

### `backend/services/roboflow_service.py`

Roboflow hosted inference adapter.

Responsibilities:

- Loads `.env` with `python-dotenv`.
- Reads `ROBOFLOW_API_KEY`, `ROBOFLOW_API_URL`, `ROBOFLOW_WORKSPACE_NAME`, `ROBOFLOW_WORKFLOW_ID`, and `ROBOFLOW_WORKFLOW_IMAGE_KEY`.
- Uses `inference-sdk` and `InferenceHTTPClient`.
- Calls `client.run_workflow(...)`.
- Resizes and JPEG-compresses images before upload.
- Uses lightweight in-memory caching.
- Uses timeout and retry handling.
- Filters non-defect classes such as `normal`, `pass`, `ok`, `good`, and `background`.
- Returns standardized detections:

```json
[
  {
    "class": "hole",
    "confidence": 0.94,
    "bbox": [x1, y1, x2, y2]
  }
]
```

Current Roboflow status:

- API key is loaded from `.env`.
- API URL is `https://serverless.roboflow.com`.
- Workflow input key `image` is accepted.
- `ROBOFLOW_MODEL_ID` is blank by design because the system uses a workflow, not direct model inference.
- The tested workflow returned empty predictions for the available local smoke image, meaning the connection works but the workflow/model did not detect a defect in that sample.

### `backend/services/hybrid_detector.py`

Detector boundary for the backend service layer.

Responsibilities:

- Calls `detect_defects()` from `roboflow_service.py`.
- Validates Roboflow output.
- Normalizes bounding boxes to pixel `xyxy` format.
- Keeps PatchCore as a lightweight fallback guardrail.
- Returns `status`, `defects`, `inference_ms`, `source`, and `patchcore`.

### `ai_core/inference/hybrid_detector.py`

Compatibility shim for old imports.

It re-exports the backend service detector so older code paths keep working.

### `backend/services/severity_engine.py`

Industrial severity classifier.

Severity levels:

- `MONITOR`
- `WARNING`
- `CRITICAL`
- `EMERGENCY`

Inputs used:

- Defect class.
- Defect confidence.
- Defect count.
- Bounding box area.
- PatchCore anomaly output.
- Isolation Forest machine sensor anomaly output.

### `backend/services/root_cause_engine.py`

Maps defect classes to likely industrial causes and actions.

Examples:

- `hole` -> needle damage or yarn break.
- `stain` -> oil leakage or contaminated fabric path.
- `needle_line` -> bent or worn needle.
- `drop_stitch` -> yarn tension instability.

Returns:

- `cause`
- `action`
- `operator_action`
- `maintenance_action`
- `machine_state`

### `backend/services/inspection_pipeline.py`

Main orchestration module.

Responsibilities:

- Generates inspection ID and timestamp.
- Selects default machine `M-05`.
- Runs hosted detection.
- Runs Isolation Forest sensor check.
- Runs severity engine.
- Runs root cause engine when a visual defect exists.
- Builds the final inspection event.
- Saves inspection.
- Saves alerts.
- Publishes Redis notification if Redis is available.
- Broadcasts WebSocket events.

### `backend/services/database_service.py`

SQLite persistence layer.

Responsibilities:

- Saves inspections to `inspections`.
- Saves alerts to `alerts`.
- Provides dashboard stats.
- Handles database failures safely.
- Redis is optional and does not block the inspection pipeline.

### `backend/services/notification_service.py`

Realtime notification support.

Responsibilities:

- Optional Redis publish for inspections and alerts.
- Falls back safely when Redis is not running.
- Provides recent alerts from Redis or SQLite fallback.

### `backend/database/models.py`

SQLAlchemy models:

- `Inspection`
- `Alert`
- `MachineState`

### `backend/database/connection.py`

SQLite database connection only.

Current database URL:

```text
sqlite:///./fabriguard.db
```

Roboflow does not use this file.

### `backend/test_roboflow.py`

Manual Roboflow smoke and diagnostic test.

Usage:

```powershell
cd E:\Amis
.\venv311\Scripts\activate
python backend/test_roboflow.py "path\to\image.jpg" --diagnose
```

Diagnostic mode reports:

- API URL.
- API key present or missing.
- Workspace.
- Workflow ID.
- Configured image key.
- Tested image input keys.
- Raw output summary.
- Parsed detections.

## Frontend Modules

### `frontend/src/components/app-shell.tsx`

Main dashboard shell.

Responsibilities:

- Navigation.
- Real-data dashboard indicator.
- Image upload panel.
- Inspect Image button.
- Result metrics.
- Live camera/image preview.
- Bounding box overlay.
- Defect table.
- Alerts center.
- Analytics panels.

The `Inspect Image` button calls `fabriGuardApi.inspectImage(file)` and sends the image to the backend `/inspect-image` route.

### `frontend/src/lib/api.ts`

Frontend API client and normalization layer.

Responsibilities:

- Calls backend REST routes.
- Sends upload to `/inspect-image`.
- Normalizes inspection payloads.
- Converts backend pixel `bbox: [x1, y1, x2, y2]` into frontend percentage overlay coordinates.
- Prevents PASS rows from being mislabeled as `sensor_anomaly`.
- Uses `normal` for clean PASS rows.
- Uses real defect class when Roboflow returns one.

### `frontend/src/hooks/use-live-fabriguard.ts`

Realtime hook.

Responsibilities:

- Connects to `ws://127.0.0.1:8000/ws/dashboard`.
- Merges live websocket inspections with backend REST inspection history.
- Merges live websocket alerts with backend alert history.
- No mock fallback is used.

## AI / ML Components

### Roboflow Hosted Workflow

Primary visual inference path.

Configured through `.env`:

```text
ROBOFLOW_API_KEY=...
ROBOFLOW_API_URL=https://serverless.roboflow.com
ROBOFLOW_WORKSPACE_NAME=nishanths-workspace-ksd7s
ROBOFLOW_WORKFLOW_ID=detect-and-classify-4
ROBOFLOW_WORKFLOW_IMAGE_KEY=image
ROBOFLOW_MODEL_ID=
ROBOFLOW_CONFIDENCE_THRESHOLD=0.55
ROBOFLOW_TIMEOUT_SECONDS=45
```

Notes:

- `ROBOFLOW_MODEL_ID` is allowed to be blank when using `run_workflow()`.
- The current issue with no predictions is not an input-key failure.
- Roboflow accepts the `image` input key.
- The tested images returned empty detection arrays from Roboflow.

### PatchCore

Lightweight fallback anomaly guardrail.

Used only when:

- Roboflow returns PASS.
- Roboflow returns weak detections.

### Isolation Forest

Machine/sensor anomaly layer.

Used for sensor health and predictive warnings. It can produce `sensor_anomaly`, but the frontend now shows that label only when the anomaly path actually triggers.

## Tools And Libraries Used

Backend:

- Python 3.11 virtual environment: `venv311`
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- python-dotenv
- inference-sdk
- Pillow
- Redis client, optional
- OpenCV support in camera stream module

Frontend:

- Next.js
- React
- TypeScript
- Zustand
- TanStack React Query
- Tailwind CSS
- Lucide React
- Recharts
- Framer Motion

Developer / verification tools:

- PowerShell
- `curl.exe`
- `git`
- TypeScript compiler: `npx tsc --noEmit`
- Python compile checks: `python -m compileall`
- Codex in-app browser verification

## Important Fixes Completed

- Integrated hosted Roboflow workflow into backend pipeline.
- Added `/inspect-image`.
- Removed frontend mock-data fallback.
- Removed visible `USE_MOCK` toggle and replaced it with `REAL DATA`.
- Fixed false `sensor_anomaly` labeling for PASS rows.
- Fixed PASS confidence display.
- Added Roboflow diagnostic script.
- Increased Roboflow timeout to 45 seconds.
- Verified workflow input key `image` is accepted.
- Confirmed frontend Inspect Image button invokes backend and Roboflow.
- Ensured backend/frontend can run on low-resource CPU without local YOLO GPU inference.

## Recent Commit Time Log

```text
1578195 | Sat May 16 10:47:53 2026 | Add Roboflow workflow diagnostics
e5a935b | Sat May 16 10:31:09 2026 | Use prediction confidence for pass inspections
921b94c | Sat May 16 10:24:00 2026 | Fix sensor anomaly labeling fallback
f47d981 | Sat May 16 10:14:41 2026 | Remove frontend mock data fallback
3745c5d | Sat May 16 08:51:41 2026 | Complete hosted inspection pipeline integration
07d2f37 | Earlier | Align upload bounding boxes to rendered image
```

## Practical Current Issue

The backend and frontend are wired correctly. Roboflow receives images through the workflow. The reason some images produce no prediction is that the hosted workflow returns empty prediction arrays for those samples.

That means the next practical work is likely inside Roboflow:

- Verify the workflow has a detection output block connected.
- Verify the workflow output exposes predictions, not only `output_image`.
- Lower workflow-side confidence threshold if it is too high.
- Test the same image inside Roboflow UI.
- Train or switch to a model version that recognizes the target fabric defects.

