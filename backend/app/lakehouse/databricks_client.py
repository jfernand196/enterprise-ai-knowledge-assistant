import json
import re
import subprocess
import time
from typing import Any, Protocol

_PROFILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_WAREHOUSE_ID = re.compile(r"^[A-Za-z0-9]+$")
_PENDING = frozenset({"PENDING", "RUNNING"})
_STATEMENT_TIMEOUT_SECONDS = 120
_POLL_DEADLINE_SECONDS = 240
_POLL_INTERVAL_SECONDS = 3


class DatabricksQueryError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class SqlClient(Protocol):
    def execute(
        self,
        statement: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]: ...


class DatabricksCliSqlClient:
    """Runs SQL through the Databricks CLI statement API.

    The CLI resolves the OAuth token from the profile. This process never
    reads or stores that token.
    """

    def __init__(self, profile: str, warehouse_id: str, catalog: str) -> None:
        if not _PROFILE.fullmatch(profile):
            raise ValueError(f"Invalid Databricks profile: {profile}")
        if not _WAREHOUSE_ID.fullmatch(warehouse_id):
            raise ValueError(f"Invalid warehouse id: {warehouse_id}")
        self._profile = profile
        self._warehouse_id = warehouse_id
        self._catalog = catalog

    def execute(
        self,
        statement: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "warehouse_id": self._warehouse_id,
            "catalog": self._catalog,
            "schema": "default",
            "statement": statement,
            "wait_timeout": "50s",
            "disposition": "INLINE",
            "format": "JSON_ARRAY",
        }
        if parameters:
            payload["parameters"] = parameters
        response = self._post("/api/2.0/sql/statements", payload)
        response = self._wait(response)
        self._raise_if_failed(response)
        return _rows(response)

    def _wait(self, response: dict[str, Any]) -> dict[str, Any]:
        deadline = time.monotonic() + _POLL_DEADLINE_SECONDS
        while response.get("status", {}).get("state") in _PENDING:
            if time.monotonic() >= deadline:
                raise DatabricksQueryError("Databricks SQL statement timed out")
            time.sleep(_POLL_INTERVAL_SECONDS)
            statement_id = response["statement_id"]
            response = self._get(f"/api/2.0/sql/statements/{statement_id}")
        return response

    def _raise_if_failed(self, response: dict[str, Any]) -> None:
        status = response.get("status", {})
        if status.get("state") == "SUCCEEDED":
            return
        error = status.get("error", {})
        message = error.get("message") or status.get("state") or "Databricks SQL statement failed"
        raise DatabricksQueryError(message)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._run(["post", path, "--json", json.dumps(payload)])

    def _get(self, path: str) -> dict[str, Any]:
        return self._run(["get", path])

    def _run(self, args: list[str]) -> dict[str, Any]:
        command = ["databricks", "api", *args, "--profile", self._profile, "-o", "json"]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=_STATEMENT_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            raise DatabricksQueryError("The databricks CLI is not installed") from exc
        except subprocess.TimeoutExpired as exc:
            raise DatabricksQueryError("The databricks CLI timed out") from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise DatabricksQueryError(detail or "The databricks CLI failed")
        try:
            body = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise DatabricksQueryError("The databricks CLI returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise DatabricksQueryError("The databricks CLI returned an unexpected payload")
        return body


def _rows(response: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = response.get("manifest") or {}
    columns = (manifest.get("schema") or {}).get("columns") or []
    names = [column["name"] for column in columns]
    types = [column.get("type_name", "STRING") for column in columns]
    raw_rows = (response.get("result") or {}).get("data_array") or []
    return [
        {name: _coerce(value, type_name) for name, type_name, value in zip(names, types, raw, strict=False)}
        for raw in raw_rows
    ]


def _coerce(value: Any, type_name: str) -> Any:
    if value is None:
        return None
    if type_name in {"BYTE", "SHORT", "INT", "LONG", "BIGINT"}:
        return int(value)
    if type_name in {"FLOAT", "DOUBLE"}:
        return float(value)
    if type_name == "BOOLEAN":
        return value if isinstance(value, bool) else str(value).lower() == "true"
    return value
