"""SSE framing + provider adapters (anthropic, openai).

Upstream bytes are framed on blank lines and handled one event at a time, so upstream chunk
boundaries never affect the output. Each text block / tool call gets its own StreamRestorer.
"""
from __future__ import annotations

from typing import Callable

import orjson

from app.restore import StreamRestorer
from app.vault import Vault, tool_policy

OnSecret = Callable[[str, str, str], None] | None  # (kind, placeholder, tool name)


class SSEFramer:
    def __init__(self):
        self._buf = b""

    def feed(self, chunk: bytes) -> list[bytes]:
        self._buf = (self._buf + chunk).replace(b"\r\n", b"\n")
        *events, self._buf = self._buf.split(b"\n\n")
        return [e + b"\n\n" for e in events]

    def flush(self) -> list[bytes]:
        rest, self._buf = self._buf, b""
        return [rest] if rest.strip() else []


def parse(event: bytes) -> tuple[str | None, str | None]:
    """Return (event name, data payload) of one SSE event."""
    name, data = None, []
    for line in event.decode().split("\n"):
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    return name, "\n".join(data) if data else None


def build(name: str | None, data: dict) -> bytes:
    head = f"event: {name}\n" if name else ""
    return head.encode() + b"data: " + orjson.dumps(data) + b"\n\n"


def tool_restorer(vault: Vault, name: str, on_secret: OnSecret) -> StreamRestorer:
    report = (lambda kind, placeholder: on_secret(kind, placeholder, name)) if on_secret else None
    if name == "Bash":  # policy depends on the full command, so decide at flush
        return StreamRestorer(vault, json_escape=True, on_secret_restore=report,
                              deferred_policy=lambda args: tool_policy("Bash", args))
    return StreamRestorer(vault, json_escape=True, policy=tool_policy(name), on_secret_restore=report)


class AnthropicAdapter:
    """One slot per content-block index: text_delta.text and input_json_delta.partial_json."""

    def __init__(self, vault: Vault, on_secret: OnSecret = None):
        self._vault = vault
        self._on_secret = on_secret
        self._slots: dict[int, tuple[StreamRestorer, str, str]] = {}  # index -> (restorer, delta type, field)

    def process(self, event: bytes) -> list[bytes]:
        name, data = parse(event)
        if data is None:
            return [event]
        msg = orjson.loads(data)
        kind = msg.get("type")
        idx = msg.get("index")

        if kind == "content_block_start":
            block = msg.get("content_block") or {}
            if block.get("type") == "text":
                self._slots[idx] = (StreamRestorer(self._vault), "text_delta", "text")
            elif block.get("type") == "tool_use":
                self._slots[idx] = (tool_restorer(self._vault, block.get("name", ""), self._on_secret),
                                    "input_json_delta", "partial_json")
            return [event]

        if kind == "content_block_delta" and idx in self._slots:
            restorer, delta_type, field = self._slots[idx]
            delta = msg.get("delta") or {}
            if delta.get("type") != delta_type:
                return [event]
            out = restorer.feed(delta.get(field, ""))
            if not out:
                return []
            delta[field] = out
            return [build(name, msg)]

        if kind == "content_block_stop" and idx in self._slots:
            return self._flush(idx) + [event]

        if kind == "message_stop":
            return self.finish() + [event]
        return [event]

    def _flush(self, idx: int) -> list[bytes]:
        restorer, delta_type, field = self._slots.pop(idx)
        rest = restorer.flush()
        if not rest:
            return []
        return [build("content_block_delta", {"type": "content_block_delta", "index": idx,
                                              "delta": {"type": delta_type, field: rest}})]

    def finish(self) -> list[bytes]:
        return [e for idx in sorted(self._slots) for e in self._flush(idx)]


class OpenAIAdapter:
    """Slots for choices[i].delta.content and choices[i].delta.tool_calls[j].function.arguments."""

    def __init__(self, vault: Vault, on_secret: OnSecret = None):
        self._vault = vault
        self._on_secret = on_secret
        self._slots: dict[tuple, StreamRestorer] = {}  # ("c", i) or ("t", i, j)
        self._base: dict = {}

    def process(self, event: bytes) -> list[bytes]:
        _, data = parse(event)
        if data is None:
            return [event]
        if data.strip() == "[DONE]":
            return self.finish() + [event]
        msg = orjson.loads(data)
        self._base = {k: msg[k] for k in ("id", "object", "created", "model") if k in msg}

        before: list[bytes] = []
        for choice in msg.get("choices") or []:
            i = choice.get("index", 0)
            delta = choice.get("delta") or {}
            if isinstance(delta.get("content"), str):
                slot = self._slots.setdefault(("c", i), StreamRestorer(self._vault))
                delta["content"] = slot.feed(delta["content"])
            for call in delta.get("tool_calls") or []:
                fn = call.get("function") or {}
                key = ("t", i, call.get("index", 0))
                if key not in self._slots:
                    self._slots[key] = tool_restorer(self._vault, fn.get("name", ""), self._on_secret)
                if isinstance(fn.get("arguments"), str):
                    fn["arguments"] = self._slots[key].feed(fn["arguments"])
            if choice.get("finish_reason"):
                # Slots this chunk already carries get their remainder appended in place (keeps order);
                # the rest go out as synthetic deltas before the finishing chunk.
                calls = {c.get("index", 0): c for c in delta.get("tool_calls") or []}
                rest = []
                for key in [k for k in self._slots if k[1] == i]:
                    if key[0] == "c" and isinstance(delta.get("content"), str):
                        delta["content"] += self._slots.pop(key).flush()
                    elif key[0] == "t" and isinstance((calls.get(key[2]) or {}).get("function", {}).get("arguments"), str):
                        calls[key[2]]["function"]["arguments"] += self._slots.pop(key).flush()
                    else:
                        rest.append(key)
                before += self._flush(rest)
        return before + [build(None, msg)]

    def _flush(self, keys: list[tuple]) -> list[bytes]:
        out = []
        for key in sorted(keys):
            rest = self._slots.pop(key).flush()
            if not rest:
                continue
            if key[0] == "c":
                delta = {"content": rest}
            else:
                delta = {"tool_calls": [{"index": key[2], "function": {"arguments": rest}}]}
            out.append(build(None, {**self._base, "choices": [{"index": key[1], "delta": delta}]}))
        return out

    def finish(self) -> list[bytes]:
        return self._flush(list(self._slots))


class StreamPipeline:
    """Bytes in, restored SSE bytes out. Never relies on upstream chunk boundaries."""

    def __init__(self, adapter: AnthropicAdapter | OpenAIAdapter):
        self._framer = SSEFramer()
        self._adapter = adapter

    def _handle(self, event: bytes) -> bytes:
        try:
            return b"".join(self._adapter.process(event))
        except Exception:
            return event  # Unparseable event: pass through. Upstream data only holds placeholders.

    def feed(self, chunk: bytes) -> bytes:
        return b"".join(self._handle(e) for e in self._framer.feed(chunk))

    def finish(self) -> bytes:
        out = b"".join(self._handle(e) for e in self._framer.flush())
        return out + b"".join(self._adapter.finish())
