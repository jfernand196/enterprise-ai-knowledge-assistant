from fastapi import Request

from app.services.chat_service import ChatService
from app.services.evaluation_service import EvaluationService
from app.services.lakehouse_service import LakehousePort
from app.services.mcp_catalog_service import McpCatalogService
from app.services.observability_service import ObservabilityService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_evaluation_service(request: Request) -> EvaluationService:
    return request.app.state.evaluation_service


def get_mcp_catalog_service(request: Request) -> McpCatalogService:
    return request.app.state.mcp_catalog_service


def get_lakehouse_service(request: Request) -> LakehousePort:
    return request.app.state.lakehouse_service


def get_observability_service(request: Request) -> ObservabilityService:
    return request.app.state.observability_service
