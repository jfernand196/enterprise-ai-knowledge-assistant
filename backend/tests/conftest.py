import os
from collections.abc import Iterator
from pathlib import Path

os.environ["LAKEHOUSE_BACKEND"] = "local"
os.environ["LLM_PROVIDER"] = "extractive"
os.environ["ORCHESTRATOR"] = "native"

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.lakehouse_service import LakehouseService


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        test_client.app.state.lakehouse_service = LakehouseService(
            tmp_path / "lakehouse",
            settings.documents_dir,
        )
        yield test_client
