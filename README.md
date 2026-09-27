# Enterprise AI Knowledge Assistant

Interview project for Lovelytics — AI Engineer. FastAPI, RAG, agents, MCP, a Databricks-style lakehouse, and LLMOps in one repo.

## Phase 7 (current)

```
User → FastAPI → Guardrails → Orchestrator
                    ├── RAG
                    └── Agent → MCP tools
                         ↓
                 Trace + metrics
```

Guardrails: prompt-injection check, tool authorization (`create_hr_request` only for `emp-2`), output validation.

Every `/chat` writes a trace: request_id, user_id, model, prompt_version, latency, tokens, cost, retrieved docs, tool calls.

- `GET /health`
- `POST /chat`
- `POST /evaluations`
- `GET /mcp/tools`
- `POST /lakehouse/runs`
- `GET /metrics`
- `GET /traces`
- `GET /traces/{request_id}`

Tokens and cost are estimates (chars/4 and published-style rates) so the pipeline is visible without a paid model. Swap the generator for a real LLM later; the trace shape stays.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the vacation policy?"}'

curl http://127.0.0.1:8000/metrics
curl http://127.0.0.1:8000/traces
```

## Test

```bash
pytest
```
