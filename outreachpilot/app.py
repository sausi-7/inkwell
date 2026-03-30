"""FastAPI application factory (Phase 1 — minimal placeholder)."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

STATIC_DIR = Path(__file__).parent / "static"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app() -> FastAPI:
    app = FastAPI(
        title="OutreachPilot",
        description="Open source AI outreach intelligence tool",
        version="0.1.0",
    )

    # Static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    async def index():
        return {"message": "OutreachPilot v0.1.0 — Web UI coming in Phase 1"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
