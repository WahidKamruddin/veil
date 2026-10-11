"""Detection rules, Luhn, entropy, and overlap resolution.

Collect spans from every rule, resolve overlaps (highest priority, then longest),
then replace in one pass so the result never depends on rule order.
"""
from __future__ import annotations

import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Iterable

# Anything shaped like one of our placeholders, e.g. [EMAIL_1] or [CREDIT_CARD_12].
PLACEHOLDER_RE = re.compile(r"\[([A-Z]+(?:_[A-Z]+)*)_(\d+)\]")

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
HEX_32_64_RE = re.compile(r"^[0-9a-fA-F]{32,64}$")
# Absolute/home/relative paths, or a relative path ending in a file extension.
PATH_RE = re.compile(r"^(?:\.{0,2}/|~/)|/.*\.[A-Za-z]{1,5}$")


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    kind: str
    prio: int
    value: str


def luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def _valid_card(value: str) -> bool:
    digits = re.sub(r"[ -]", "", value)
    return 13 <= len(digits) <= 19 and luhn(digits)


def _valid_secret(value: str) -> bool:
    if UUID_RE.match(value) or HEX_32_64_RE.match(value) or PATH_RE.search(value):
        return False
    return shannon_entropy(value) > 3.5


@dataclass(frozen=True)
class Rule:
    kind: str
    prio: int
    pattern: re.Pattern
    group: int = 0
    validator: Callable[[str], bool] | None = None


RULES: list[Rule] = [
    # User-typed placeholder lookalikes are escaped so they can't collide with real ones.
    Rule("ESCAPED", 200, PLACEHOLDER_RE),
    Rule("PRIVATE_KEY", 100, re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z0-9 ]*PRIVATE KEY-----")),
    Rule("ANTHROPIC_KEY", 95, re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    Rule("OPENAI_KEY", 90, re.compile(r"sk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{20,}")),
    Rule("GITHUB_TOKEN", 90, re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,}")),
    Rule("AWS_KEY", 90, re.compile(r"\b(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}\b")),
    Rule("STRIPE_KEY", 90, re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|\bwhsec_[A-Za-z0-9]{16,}")),
    Rule("OTHER_TOKEN", 85, re.compile(
        r"xox[baprs]-[A-Za-z0-9-]{10,}"
        r"|AIza[0-9A-Za-z_-]{35}"
        r"|eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
        r"|[A-Za-z][A-Za-z0-9+.-]*://[^\s:/@]+:[^\s/@]+@[^\s/]+")),
    Rule("SSN", 80, re.compile(r"\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")),
    Rule("CREDIT_CARD", 80, re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), validator=_valid_card),
    Rule("EMAIL", 70, re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    Rule("SECRET", 60, re.compile(
        r"(?i:key|token|secret|passw\w*|bearer)[\w\s\"']{0,20}[:=]\s*[\"']?([A-Za-z0-9_\-+/=.~]{16,})"),
        group=1, validator=_valid_secret),
]

PHONE_PRIO = 65


def _phone_enabled(phone: bool | None) -> bool:
    return os.environ.get("VEIL_PHONE") == "1" if phone is None else phone


def _phone_spans(text: str) -> list[Span]:
    try:
        import phonenumbers
    except ImportError:
        return []
    return [Span(m.start, m.end, "PHONE", PHONE_PRIO, m.raw_string)
            for m in phonenumbers.PhoneNumberMatcher(text, "US")]


def resolve(spans: Iterable[Span]) -> list[Span]:
    """Keep non-overlapping spans, preferring highest priority, then longest. Sorted by start."""
    accepted: list[Span] = []
    for s in sorted(spans, key=lambda s: (-s.prio, -(s.end - s.start), s.start)):
        if all(s.end <= a.start or s.start >= a.end for a in accepted):
            accepted.append(s)
    return sorted(accepted, key=lambda s: s.start)


def find_spans(text: str, phone: bool | None = None, rules: list[Rule] | None = None) -> list[Span]:
    spans: list[Span] = []
    for rule in RULES if rules is None else rules:
        for m in rule.pattern.finditer(text):
            value = m.group(rule.group)
            if rule.validator and not rule.validator(value):
                continue
            spans.append(Span(m.start(rule.group), m.end(rule.group), rule.kind, rule.prio, value))
    if _phone_enabled(phone):
        spans.extend(_phone_spans(text))
    return resolve(spans)


def redact(text: str, tokenize: Callable[[str, str], str], phone: bool | None = None,
           rules: list[Rule] | None = None) -> str:
    """Replace every resolved span with tokenize(kind, value), in one pass."""
    out: list[str] = []
    pos = 0
    for s in find_spans(text, phone, rules):
        out.append(text[pos:s.start])
        out.append(tokenize(s.kind, s.value))
        pos = s.end
    out.append(text[pos:])
    return "".join(out)
