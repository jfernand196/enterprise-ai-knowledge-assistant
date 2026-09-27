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
| `backend/app/api` | Routes and dependencies |
| `backend/app/services` | Chat orchestration and one service per use case |
| `backend/app/rag` | Chunking, TF-IDF embeddings, retrieval, rerank, Gemini generator |
| `backend/app/agent` | Planner, tools, answer writer |
| `backend/app/mcp` | In-process MCP server and client for the HR tools |
| `backend/app/lakehouse` | Bronze, silver, gold pipeline (local JSON or Databricks Delta) |
| `backend/app/llmops` | Guardrails, traces, token and cost estimates |
| `backend/tests` | Pytest suite that runs without Databricks or an API key |
| `frontend` | Vite + React chat UI |
| `data` | Policy documents, employees, evaluation questions |
| `docs` | Architecture notes |

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
cd backend && .venv/bin/pytest
cd frontend && npx tsc -b
```
