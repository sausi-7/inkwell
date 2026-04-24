"""FastAPI application factory for the Inkwell web UI.

Single-user localhost tool. Binds to 127.0.0.1 by default (see __main__.py).
No auth — intended to run on your own machine. The BYOK LLM key is never
persisted server-side; it lives in browser localStorage and rides on the
X-LLM-Key header when the user clicks "Draft".
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from inkwell.routes import api_profile, api_scan, api_settings, api_signals, pages

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(
        title="Inkwell",
        description="Open source AI outreach intelligence tool",
        version="0.1.0",
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(pages.router)
    app.include_router(api_profile.router, prefix="/api")
    app.include_router(api_settings.router, prefix="/api")
    app.include_router(api_scan.router, prefix="/api")
    app.include_router(api_signals.router, prefix="/api")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
