from __future__ import annotations

import asyncio

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._active.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._active.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        async with self._lock:
            clients = list(self._active)

        if not clients:
            return

        results = await asyncio.gather(
            *(client.send_json(payload) for client in clients),
            return_exceptions=True,
        )

        stale = [
            client
            for client, result in zip(clients, results)
            if isinstance(result, Exception)
        ]
        if stale:
            async with self._lock:
                for client in stale:
                    self._active.discard(client)

    async def count(self) -> int:
        async with self._lock:
            return len(self._active)


dashboard_manager = ConnectionManager()
