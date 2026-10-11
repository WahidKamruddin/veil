"""Vault (placeholder <-> real value) and per-session store with TTL + size cap.

Values live in process memory only. Never log them, never write them to disk.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable

from app import detect

# Kinds that restore everywhere. Every other kind is a secret.
ALWAYS_RESTORE = frozenset({"EMAIL", "PHONE", "SSN", "CREDIT_CARD", "ESCAPED"})

# Tools allowed to receive restored secrets in their arguments.
SECRET_TOOLS = frozenset({"Edit", "Write"})
EXFIL_COMMANDS_RE = re.compile(r"\b(?:curl|wget|nc|ncat|ssh|scp)\b")


@dataclass(frozen=True)
class Policy:
    allow_secrets: bool


PLAIN = Policy(allow_secrets=False)


def tool_policy(tool_name: str, args_text: str = "") -> Policy:
    """Secrets restore only for Edit, Write, and Bash commands with no network/exfil tools."""
    if tool_name in SECRET_TOOLS:
        return Policy(allow_secrets=True)
    if tool_name == "Bash" and not EXFIL_COMMANDS_RE.search(args_text):
        return Policy(allow_secrets=True)
    return PLAIN


class Vault:
    def __init__(self, memo_size: int = 2048, phone: bool | None = None):
        self._by_value: dict[tuple[str, str], str] = {}
        self._by_placeholder: dict[str, tuple[str, str]] = {}
        self._counters: dict[str, int] = {}
        self._memo: OrderedDict[str, str] = OrderedDict()
        self._memo_size = memo_size
        self._phone = phone

    def __repr__(self) -> str:
        return f"Vault(entries={len(self._by_placeholder)})"

    def __len__(self) -> int:
        return len(self._by_placeholder)

    def tokenize(self, kind: str, value: str) -> str:
        key = (kind, value.lower() if kind == "EMAIL" else value)
        placeholder = self._by_value.get(key)
        if placeholder is None:
            n = self._counters.get(kind, 0) + 1
            self._counters[kind] = n
            placeholder = f"[{kind}_{n}]"
            self._by_value[key] = placeholder
            self._by_placeholder[placeholder] = (kind, value)
        return placeholder

    def sanitize(self, text: str) -> str:
        # Memo stays valid: mappings only ever grow, and tokenize is deterministic.
        cached = self._memo.get(text)
        if cached is not None:
            self._memo.move_to_end(text)
            return cached
        # Our own placeholders come back in resent history: keep the ones issued before
        # this text, escape every other lookalike (including ones minted in this pass).
        issued = set(self._by_placeholder)

        def tokenize(kind: str, value: str) -> str:
            if kind == "ESCAPED" and value in issued:
                return value
            return self.tokenize(kind, value)

        result = detect.redact(text, tokenize, phone=self._phone)
        self._memo[text] = result
        if len(self._memo) > self._memo_size:
            self._memo.popitem(last=False)
        return result

    def restore(self, text: str, json_escape: bool = False, policy: Policy = PLAIN,
                on_secret_restore: Callable[[str, str], None] | None = None) -> str:
        """Replace known placeholders allowed by policy. Unknown ones stay as-is. Never raises."""
        def sub(m: re.Match) -> str:
            entry = self._by_placeholder.get(m.group(0))
            if entry is None:
                return m.group(0)
            kind, value = entry
            if kind not in ALWAYS_RESTORE:
                if not policy.allow_secrets:
                    return m.group(0)
                if on_secret_restore is not None:
                    on_secret_restore(kind, m.group(0))
            return json.dumps(value)[1:-1] if json_escape else value

        try:
            return detect.PLACEHOLDER_RE.sub(sub, text)
        except Exception:
            return text


class SessionStore:
    """Vaults keyed by sha256(auth header + optional X-Session-Id), with TTL and LRU size cap."""

    def __init__(self, ttl: float = 3600.0, max_sessions: int = 1000,
                 clock: Callable[[], float] = time.monotonic, phone: bool | None = None):
        self._ttl = ttl
        self._max = max_sessions
        self._clock = clock
        self._phone = phone
        self._sessions: OrderedDict[str, tuple[Vault, float]] = OrderedDict()

    def __len__(self) -> int:
        return len(self._sessions)

    @staticmethod
    def key(auth: str, session_id: str | None = None) -> str:
        return hashlib.sha256(f"{auth}\0{session_id or ''}".encode()).hexdigest()

    def get(self, auth: str, session_id: str | None = None) -> Vault:
        now = self._clock()
        # Oldest-accessed first, so stop at the first live session.
        while self._sessions:
            oldest_key, (_, last) = next(iter(self._sessions.items()))
            if now - last < self._ttl:
                break
            del self._sessions[oldest_key]

        k = self.key(auth, session_id)
        entry = self._sessions.pop(k, None)
        vault = entry[0] if entry else Vault(phone=self._phone)
        self._sessions[k] = (vault, now)
        while len(self._sessions) > self._max:
            self._sessions.popitem(last=False)
        return vault
