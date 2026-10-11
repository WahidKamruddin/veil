# Veil progress

- [x] 1. Scaffold, pyproject, pytest config, PROGRESS.md; detect.py + vault.py + tests (incl. false-positive corpus)
  - notes: 54 tests green. User-typed `[EMAIL_1]` lookalikes become `[ESCAPED_n]` (always restore), but placeholders already issued in an earlier message pass through unchanged; SECRET rule skips file paths; restore policy + `on_secret_restore` hook built into vault now (wire-tap hookup in step 4); CC regex anchored to end on a digit; pytest-asyncio added for step 2.
- [x] 2. Non-streaming proxy + demo/mock_upstream.py; verify end to end with curl
  - notes: 67 tests green + curl verified via uvicorn (mock :9000, Veil :8080). Catch-all paths also sanitize JSON bodies (zero-trust; count_tokens carries full history). Restore policy applied to tool calls already. Streams pass through raw until step 3. Upstreams via VEIL_ANTHROPIC_UPSTREAM / VEIL_OPENAI_UPSTREAM.
- [ ] 3. Streaming restorer + both adapters + tool-call slots; split-at-every-byte fuzz test
  - notes:
- [ ] 4. Wire-tap, restore policy, README, demo/demo.sh, latency script
  - notes:
