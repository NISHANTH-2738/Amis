from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.api.websocket.manager import dashboard_manager
from backend.services.database_service import get_todays_stats


router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await dashboard_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "stats",
                "payload": get_todays_stats(),
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await dashboard_manager.disconnect(websocket)
    except Exception:
        await dashboard_manager.disconnect(websocket)
