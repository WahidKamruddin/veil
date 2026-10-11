# Veil

**The model never sees your secrets.**

Veil is a local reverse proxy between LLM clients (Claude Code, SDK apps, agents) and model APIs. It redacts secrets and PII from requests before they go upstream and restores them in responses.

```
ANTHROPIC_BASE_URL=http://localhost:8080 claude
```

## Out of scope

Images and files, Realtime/WebSocket, embeddings, Bedrock/Vertex (SigV4), NER for names and addresses.

## Repo layout

- `backend/`: the Python proxy (`cd backend && pip install -e '.[dev]' && pytest`)
- `landing/`: the landing page, Vite + React (`cd landing && npm install && npm run dev`)
