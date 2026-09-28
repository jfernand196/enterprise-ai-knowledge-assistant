# Enterprise AI Knowledge Assistant

Interview project for Lovelytics — AI Engineer. FastAPI, RAG, an HR agent with MCP tools, a Databricks medallion lakehouse, LLMOps, and a React chat UI.

```
React → FastAPI → Guardrails → Orchestrator (native | langchain | langgraph)
                                  ├── RAG over the Databricks gold table
                                  └── Agent → MCP tools (profile, balance, HR request)
                                        ↓
                                Trace: tokens, latency, cost
```

Policy questions go to RAG. Questions about the speaker (vacation balance, time off requests) go to the agent. Only `emp-2` (Ana Gomez) may create HR requests.

The design choices and the reason for each tool are in [docs/arquitectura.md](docs/arquitectura.md).

## Orchestrators

`ORCHESTRATOR` in `.env` picks who runs the flow. All three share the index, the MCP tools, authorization, and tracing.

| Value | Code | Study guide |
| --- | --- | --- |
| `native` (default) | `backend/app/rag`, `backend/app/agent` | [docs/arquitectura.md](docs/arquitectura.md) |
| `langchain` | `backend/app/lc` | [docs/langchain.md](docs/langchain.md) |
| `langgraph` | `backend/app/lg` | [docs/langgraph.md](docs/langgraph.md) |

Restart uvicorn after changing it. Traces record the choice as `prompt_version` (`v1`, `langchain-v1`, `langgraph-v1`).

## LLMOps

- **Traces:** every `/chat` writes latency, tokens, cost, model, route, documents, and tools to `data/llmops/traces.jsonl` (gitignored). They survive a restart.
- **Feedback:** 👍 / 👎 under each answer, stored on the trace.
- **Metrics:** `/metrics` totals plus breakdowns by orchestrator and by model, so the three orchestrators can be compared.
- **Evaluation:** seven golden cases covering policy RAG, the agent, authorization, and a prompt injection. Every run is kept, so a regression shows up.
- **Quality gate:** `python -m app.llmops.gate --min-pass-rate 0.85` exits 1 when the pass rate drops.
- **Panel:** `/ops` in the UI shows all of the above.

Details and trade-offs are in [docs/arquitectura.md](docs/arquitectura.md#llmops).

## Layout

| Path | Contents |
| --- | --- |
| `backend/app/api` | Routes and dependencies |
| `backend/app/services` | Chat orchestration and one service per use case |
| `backend/app/rag` | Chunking, TF-IDF embeddings, retrieval, rerank, Gemini generator |
| `backend/app/agent` | Planner, tools, answer writer |
| `backend/app/mcp` | In-process MCP server and client for the HR tools |
| `backend/app/lakehouse` | Bronze, silver, gold pipeline (local JSON or Databricks Delta) |
| `backend/app/llmops` | Guardrails, persistent traces, token and cost estimates, quality gate |
| `backend/app/lc` | The same RAG and agent built with LangChain |
| `backend/app/lg` | The whole flow as a LangGraph state graph |
| `backend/tests` | Pytest suite that runs without Databricks or an API key |
| `frontend` | Vite + React chat UI |
| `data` | Policy documents, employees, evaluation cases; `data/llmops` holds local traces (gitignored) |
| `docs` | Architecture notes and LangChain / LangGraph study guides |

`.env` and `data/` stay at the repository root. The backend reads both from there.

## Setup

```bash
cp .env.example .env
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Fill in `.env`. For Databricks, log in once with `databricks auth login --profile <profile>`; the app calls the CLI and never reads the token. Set `LAKEHOUSE_BACKEND=local` and `LLM_PROVIDER=extractive` to run with no external services.

## Run

Backend, port 8000:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend, port 5173 (proxies `/api` to the backend):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The **Guía** button lists what to ask and the expected answer. Each reply shows input tokens, output tokens, latency, and feedback buttons. **Ops** opens the LLMOps panel at http://localhost:5173/ops. The header button switches the UI between Spanish and English.

## API

- `GET /health`
- `POST /chat`
- `POST /evaluations` runs the golden set; `GET /evaluations` lists past runs
- `POST /feedback`
- `GET /mcp/tools`
- `POST /lakehouse/runs`
- `GET /metrics`
- `GET /traces?limit=50`
- `GET /traces/{request_id}`

## Test

```bash
cd backend && .venv/bin/pytest
cd backend && .venv/bin/python -m app.llmops.gate --min-pass-rate 0.85
cd frontend && npx tsc -b
```

The LangChain and LangGraph tests use fake chat models, so they also run offline.
