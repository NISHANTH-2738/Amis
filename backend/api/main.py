from __future__ import annotations

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.api.routes.health import router as health_router
from backend.api.routes.inspect import router as inspect_router
from backend.api.routes.monitoring import router as monitoring_router
from backend.api.websocket.routes import router as websocket_router
from backend.database.connection import create_tables


def create_app() -> FastAPI:
    app = FastAPI(
        title="Industrial AI Inspection API",
        description="Real-time Industry 4.0 defect detection and monitoring.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(inspect_router)
    app.include_router(monitoring_router)
    app.include_router(websocket_router)

    @app.on_event("startup")
    async def startup():
        create_tables()
        print("Industrial AI Inspection API started")
        print("Docs: http://localhost:8000/docs")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
