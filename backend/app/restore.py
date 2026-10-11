"""StreamRestorer: restores placeholders in one stream slot (a text block or a tool call's arguments).

Holds back only the shortest tail that could still become a placeholder, so cost stays O(chunk)
and a placeholder split across deltas ([, EM, AIL, _, 1, ]) is never emitted half-restored.
"""
from __future__ import annotations

import re
from typing import Callable

from app.vault import PLAIN, Policy, Vault

# A '[' followed by what could still grow into "[KIND_N]" (no closing bracket yet).
PENDING_RE = re.compile(r"\[[A-Z_]*\d*$")
MAX_HOLD = 24


class StreamRestorer:
    def __init__(self, vault: Vault, json_escape: bool = False, policy: Policy = PLAIN,
                 deferred_policy: Callable[[str], Policy] | None = None,
                 on_secret_restore: Callable[[str, str], None] | None = None):
        """deferred_policy: buffer the whole slot and pick the policy from its full text at flush
        (used for Bash, whose command must be complete before we know it is safe)."""
        self._vault = vault
        self._json_escape = json_escape
        self._policy = policy
        self._deferred = deferred_policy
        self._on_secret = on_secret_restore
        self._buf = ""

    def _restore(self, text: str, policy: Policy) -> str:
        return self._vault.restore(text, self._json_escape, policy, self._on_secret)

    def feed(self, text: str) -> str:
        self._buf += text
        if self._deferred is not None:
            return ""
        cut = len(self._buf)
        start = self._buf.rfind("[", max(0, len(self._buf) - MAX_HOLD))
        if start != -1 and PENDING_RE.match(self._buf, start):
            cut = start
        # Cut before substituting so a complete placeholder is never split.
        emit, self._buf = self._buf[:cut], self._buf[cut:]
        return self._restore(emit, self._policy) if emit else ""

    def flush(self) -> str:
        rest, self._buf = self._buf, ""
        if not rest:
            return ""
        policy = self._deferred(rest) if self._deferred is not None else self._policy
        return self._restore(rest, policy)
