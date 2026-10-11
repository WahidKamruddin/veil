"""Veil app + lifespan (one shared httpx AsyncClient)."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.proxy import router
from app.vault import SessionStore


def create_app(transport: httpx.AsyncBaseTransport | None = None,
               anthropic_base: str | None = None, openai_base: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.anthropic_base = (anthropic_base or os.environ.get(
            "VEIL_ANTHROPIC_UPSTREAM", "https://api.anthropic.com")).rstrip("/")
        app.state.openai_base = (openai_base or os.environ.get(
            "VEIL_OPENAI_UPSTREAM", "https://api.openai.com")).rstrip("/")
        app.state.sessions = SessionStore()
        async with httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(600, connect=10)) as client:
            app.state.client = client
            yield

    app = FastAPI(title="Veil", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # keep logs to Veil's own lines
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("VEIL_PORT", "8080")))
