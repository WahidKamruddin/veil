"""JSON string-leaf walker. Applies fn to string leaves only; never touches keys or skipped fields."""
from __future__ import annotations

from typing import Any, Callable

# Structural or signed fields: modifying them breaks routing, ids, or thinking signatures.
SKIP_KEYS = frozenset({
    "model", "role", "type", "id", "tool_use_id", "tool_call_id",
    "media_type", "data", "signature", "thinking",
})


def walk(obj: Any, fn: Callable[[str], str], skip: frozenset[str] = SKIP_KEYS) -> Any:
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [walk(v, fn, skip) for v in obj]
    if isinstance(obj, dict):
        return {k: v if k in skip else walk(v, fn, skip) for k, v in obj.items()}
    return obj
