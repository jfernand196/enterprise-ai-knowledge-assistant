# Enterprise AI Knowledge Assistant

Interview project for Lovelytics — AI Engineer. FastAPI, RAG, an HR agent with MCP tools, a Databricks medallion lakehouse, LLMOps, and a React chat UI.

```
React → FastAPI → Guardrails → Orchestrator
                                  ├── RAG over the Databricks gold table
                                  └── Agent → MCP tools (profile, balance, HR request)
                                        ↓
                                Trace: tokens, latency, cost
```

Policy questions go to RAG. Questions about the speaker (vacation balance, time off requests) go to the agent. Only `emp-2` (Ana Gomez) may create HR requests.

The design choices and the reason for each tool are in [docs/arquitectura.md](docs/arquitectura.md).

## Layout

| Path | Contents |
| --- | --- |
| `app/api` | Routes and dependencies |
| `app/services` | Chat orchestration and one service per use case |
| `app/rag` | Chunking, TF-IDF embeddings, retrieval, rerank, Gemini generator |
| `app/agent` | Planner, tools, answer writer |
| `app/mcp` | In-process MCP server and client for the HR tools |
| `app/lakehouse` | Bronze, silver, gold pipeline (local JSON or Databricks Delta) |
| `app/llmops` | Guardrails, traces, token and cost estimates |
| `data` | Policy documents, employees, evaluation questions |
| `frontend` | Vite + React chat UI |
| `tests` | Pytest suite that runs without Databricks or an API key |

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`. For Databricks, log in once with `databricks auth login --profile <profile>`; the app calls the CLI and never reads the token. Set `LAKEHOUSE_BACKEND=local` and `LLM_PROVIDER=extractive` to run with no external services.

## Run

Backend, port 8000:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend, port 5173 (proxies `/api` to the backend):

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The **Guía** button lists what to ask and the expected answer.

## API

- `GET /health`
- `POST /chat`
- `POST /evaluations`
- `GET /mcp/tools`
- `POST /lakehouse/runs`
- `GET /metrics`
- `GET /traces`
- `GET /traces/{request_id}`

## Test

```bash
.venv/bin/pytest
cd frontend && npx tsc -b
```
