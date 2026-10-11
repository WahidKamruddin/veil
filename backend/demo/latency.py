"""Veil latency: p50 added latency on a ~10 KB request, and TTFT delta, Veil vs direct to the mock.

Expects the mock on :9000 and Veil on :8080 (demo/demo.sh latency starts both).
Each request body is unique so Veil's sanitize memo never hits (worst case).
"""
from __future__ import annotations

import statistics
import sys
import time

import httpx

DIRECT = "http://127.0.0.1:9000"
VEIL = "http://127.0.0.1:8080"
HEADERS = {"x-api-key": "latency-key-fake", "anthropic-version": "2023-06-01"}
N = int(sys.argv[1]) if len(sys.argv) > 1 else 200

# ~10 KB of prose with PII and fake secrets sprinkled in.
PARAGRAPH = ("Please review the deploy notes from ops@example.com. The staging card 4111 1111 1111 1111 "
             "was used for tests, key " + "AKIA" + "FAKEFAKEFAKE0000" + " rotated, ticket 123-45-6789. ")


def body(i: int, stream: bool) -> dict:
    text = f"run {i}: " + PARAGRAPH * (10_240 // len(PARAGRAPH))
    return {"model": "mock", "max_tokens": 10, "stream": stream, "messages": [{"role": "user", "content": text}]}


def total_ms(client: httpx.Client, base: str, i: int) -> float:
    t = time.perf_counter()
    client.post(f"{base}/v1/messages", json=body(i, False), headers=HEADERS).raise_for_status()
    return (time.perf_counter() - t) * 1000


def ttft_ms(client: httpx.Client, base: str, i: int) -> float:
    t = time.perf_counter()
    buf, first = b"", None
    with client.stream("POST", f"{base}/v1/messages", json=body(i, True), headers=HEADERS) as r:
        for chunk in r.iter_raw():
            if first is None:
                buf += chunk
                if b"text_delta" in buf:  # first content token reached the client
                    first = (time.perf_counter() - t) * 1000
    # Drained to the end, so no leftover server work skews the next measurement.
    if first is None:
        raise RuntimeError("no text delta in stream")
    return first


def p50(xs: list[float]) -> float:
    return statistics.median(xs)


def main() -> None:
    size = len(httpx.Request("POST", VEIL, json=body(0, False)).content)
    with httpx.Client(timeout=30) as client:
        for base in (DIRECT, VEIL):  # warm up connections and imports
            total_ms(client, base, -1)
            ttft_ms(client, base, -1)
        direct, veil, d_ttft, v_ttft = [], [], [], []
        for i in range(N):  # interleave so drift hits both paths equally
            direct.append(total_ms(client, DIRECT, i))
            veil.append(total_ms(client, VEIL, i))
            d_ttft.append(ttft_ms(client, DIRECT, i))
            v_ttft.append(ttft_ms(client, VEIL, i))

    print(f"Veil latency  ({N} runs, request body {size / 1024:.1f} KB)")
    print(f"  non-streaming p50   direct {p50(direct):6.2f} ms   via Veil {p50(veil):6.2f} ms"
          f"   added {p50(veil) - p50(direct):+6.2f} ms")
    print(f"  TTFT p50            direct {p50(d_ttft):6.2f} ms   via Veil {p50(v_ttft):6.2f} ms"
          f"   delta {p50(v_ttft) - p50(d_ttft):+6.2f} ms")


if __name__ == "__main__":
    main()
