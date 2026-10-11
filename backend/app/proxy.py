"""Veil routes + request/response handling.

Sanitize the request body before anything goes upstream (fail closed), restore the response.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import orjson
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTask

from app.vault import PLAIN, Vault, tool_policy
from app.walk import SKIP_KEYS, walk

log = logging.getLogger("veil")
router = APIRouter()

DROP_REQUEST_HEADERS = frozenset({"host", "content-length", "connection", "transfer-encoding"})
DROP_RESPONSE_HEADERS = frozenset({"content-length", "connection", "transfer-encoding", "content-encoding"})
FAILED_CLOSED = {"error": "sanitizer_failed_closed"}


def provider_for(path: str, headers) -> str:
    if path.startswith("/v1/messages") or "anthropic-version" in headers or "x-api-key" in headers:
        return "anthropic"
    return "openai"


def restore_anthropic(body: dict, vault: Vault) -> dict:
    for block in body.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "tool_use":
            args = block.get("input")
            policy = tool_policy(block.get("name", ""), orjson.dumps(args).decode())
            block["input"] = walk(args, lambda s: vault.restore(s, policy=policy))
    return walk(body, vault.restore, SKIP_KEYS | {"input"})


def restore_openai(body: dict, vault: Vault) -> dict:
    for choice in body.get("choices") or []:
        message = choice.get("message") if isinstance(choice, dict) else None
        for call in (message or {}).get("tool_calls") or []:
            fn = call.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                fn["arguments"] = vault.restore(args, json_escape=True,
                                                policy=tool_policy(fn.get("name", ""), args))
    return walk(body, vault.restore, SKIP_KEYS | {"arguments"})


def restore_body(body: Any, vault: Vault, provider: str) -> Any:
    if not isinstance(body, dict):
        return walk(body, lambda s: vault.restore(s, policy=PLAIN))
    return restore_anthropic(body, vault) if provider == "anthropic" else restore_openai(body, vault)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(request: Request, path: str) -> Response:
    started = time.perf_counter()
    state = request.app.state
    provider = provider_for(request.url.path, request.headers)
    auth = request.headers.get("x-api-key") or request.headers.get("authorization") or ""
    vault = state.sessions.get(auth, request.headers.get("x-session-id"))

    raw = await request.body()
    payload = raw
    if raw:
        try:
            payload = orjson.dumps(walk(orjson.loads(raw), vault.sanitize))
        except Exception:
            log.warning("Veil %s %s -> 500 sanitizer failed closed", request.method, request.url.path)
            return JSONResponse(FAILED_CLOSED, status_code=500)

    base = state.anthropic_base if provider == "anthropic" else state.openai_base
    url = base + request.url.path + (f"?{request.url.query}" if request.url.query else "")
    headers = {k: v for k, v in request.headers.items() if k.lower() not in DROP_REQUEST_HEADERS}
    headers["accept-encoding"] = "identity"

    client: httpx.AsyncClient = state.client
    upstream_req = client.build_request(request.method, url, headers=headers, content=payload)
    try:
        upstream = await client.send(upstream_req, stream=True)
    except httpx.HTTPError:
        return JSONResponse({"error": "upstream_unreachable"}, status_code=502)

    out_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in DROP_RESPONSE_HEADERS}

    if upstream.headers.get("content-type", "").startswith("text/event-stream"):
        # Step 3 replaces this raw passthrough with the StreamRestorer pipeline.
        out_headers.update({"cache-control": "no-cache", "x-accel-buffering": "no"})
        return StreamingResponse(upstream.aiter_raw(), status_code=upstream.status_code,
                                 headers=out_headers, background=BackgroundTask(upstream.aclose))

    body = await upstream.aread()
    await upstream.aclose()
    try:
        body = orjson.dumps(restore_body(orjson.loads(body), vault, provider))
    except Exception:
        pass  # Not JSON (or unexpected shape): pass through. It only holds placeholders.
    log.info("Veil %s %s -> %d (%.1f ms)", request.method, request.url.path,
             upstream.status_code, (time.perf_counter() - started) * 1000)
    return Response(body, status_code=upstream.status_code, headers=out_headers)
