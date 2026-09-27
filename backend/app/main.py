from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent.gemini_agent import GeminiAnswerWriter, GeminiPlanner
from app.agent.tools import (
    CreateHrRequestTool,
    GetEmployeeProfileTool,
    GetVacationBalanceTool,
    SearchDocumentsTool,
    ToolRegistry,
)
from app.api.routes import chat, evaluations, health, lakehouse, mcp_tools, observability
from app.core.config import settings
from app.hr.repository import HrRepository
from app.knowledge.gold import load_gold_documents
from app.knowledge.index import build_knowledge_index
from app.lakehouse.databricks_client import DatabricksCliSqlClient
from app.llmops.guardrails import GuardrailRejectedError
from app.llmops.tracing import TraceStore
from app.mcp.client import McpClient, McpToolAdapter
from app.mcp.server import McpServer
from app.services.agent_service import AgentService
from app.services.chat_service import ChatService
from app.services.evaluation_service import EvaluationService
from app.services.lakehouse_service import build_lakehouse_service
from app.services.mcp_catalog_service import McpCatalogService
from app.services.observability_service import ObservabilityService
from app.rag.gemini import GeminiGroundedGenerator, build_chat_generator
from app.services.rag_service import RagService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    documents = None
    if settings.lakehouse_backend == "databricks":
        documents = load_gold_documents(
            DatabricksCliSqlClient(
                settings.databricks_profile,
                settings.databricks_warehouse_id,
                settings.databricks_catalog,
            ),
            settings.databricks_catalog,
        )
    generator = build_chat_generator(
        provider=settings.llm_provider,
        gemini_api_key=settings.gemini_api_key,
        model_id=settings.model_id,
        groq_api_key=settings.groq_api_key,
        groq_model_id=settings.groq_model_id,
    )
    index = build_knowledge_index(
        documents_dir=settings.documents_dir,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
        top_k=settings.top_k,
        candidate_k=settings.candidate_k,
        documents=documents,
        generator=generator,
    )
    rag_service = RagService(index)
    hr_repository = HrRepository.from_json(settings.employees_path)
    mcp_server = McpServer(
        [
            GetEmployeeProfileTool(hr_repository),
            GetVacationBalanceTool(hr_repository),
            CreateHrRequestTool(hr_repository),
        ]
    )
    mcp_client = McpClient(mcp_server)
    registry = ToolRegistry(
        [
            SearchDocumentsTool(index.retriever),
            *[McpToolAdapter(mcp_client, spec) for spec in mcp_client.list_tools()],
        ]
    )
    traces = TraceStore()
    planner = None
    answer_writer = None
    if isinstance(generator, GeminiGroundedGenerator):
        planner = GeminiPlanner(generator)
        answer_writer = GeminiAnswerWriter(generator)
    writers = frozenset(settings.hr_writers.split(","))
    agent_service = AgentService(
        registry,
        planner=planner,
        writers=writers,
        answer_writer=answer_writer,
    )
    prompt_version = settings.prompt_version
    orchestrator = None
    if settings.orchestrator == "langgraph":
        from app.lg.service import build_langgraph_service

        orchestrator = build_langgraph_service(
            index.retriever,
            registry,
            writers,
            gemini_api_key=settings.gemini_api_key,
            model_id=settings.model_id,
            groq_api_key=settings.groq_api_key,
            groq_model_id=settings.groq_model_id,
        )
        prompt_version = f"langgraph-{settings.prompt_version}"
    elif settings.orchestrator == "langchain":
        from app.lc.services import build_langchain_services

        rag_service, agent_service = build_langchain_services(
            index.retriever,
            registry,
            writers,
            gemini_api_key=settings.gemini_api_key,
            model_id=settings.model_id,
            groq_api_key=settings.groq_api_key,
            groq_model_id=settings.groq_model_id,
        )
        prompt_version = f"langchain-{settings.prompt_version}"
    app.state.chat_service = ChatService(
        rag_service,
        agent_service,
        traces,
        model=settings.model_name,
        prompt_version=prompt_version,
        input_rate=settings.input_token_rate,
        output_rate=settings.output_token_rate,
        orchestrator=orchestrator,
    )
    app.state.evaluation_service = EvaluationService(orchestrator or rag_service, settings.eval_path)
    app.state.mcp_catalog_service = McpCatalogService(mcp_client)
    app.state.lakehouse_service = build_lakehouse_service(
        backend=settings.lakehouse_backend,
        documents_dir=settings.documents_dir,
        lakehouse_dir=settings.lakehouse_dir,
        profile=settings.databricks_profile,
        warehouse_id=settings.databricks_warehouse_id,
        catalog=settings.databricks_catalog,
    )
    app.state.observability_service = ObservabilityService(traces)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, tags=["health"])
app.include_router(chat.router, tags=["chat"])
app.include_router(evaluations.router, tags=["evaluations"])
app.include_router(mcp_tools.router, tags=["mcp"])
app.include_router(lakehouse.router, tags=["lakehouse"])
app.include_router(observability.router, tags=["llmops"])


@app.exception_handler(GuardrailRejectedError)
async def guardrail_rejected_handler(
    _request: Request,
    exc: GuardrailRejectedError,
) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.reason})
