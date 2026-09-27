from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    app_name: str = "Enterprise AI Knowledge Assistant"
    app_version: str = "0.7.0"
    model_name: str = "grounded-extractive-v1"
    prompt_version: str = "v1"
    llm_provider: str = "extractive"
    model_id: str = "gemini-3.6-flash"
    groq_model_id: str = "openai/gpt-oss-120b"
    orchestrator: str = "native"
    gemini_api_key: str = ""
    groq_api_key: str = ""
    input_token_rate: float = 0.15
    output_token_rate: float = 0.60
    hr_writers: str = "emp-2"
    documents_dir: Path = PROJECT_ROOT / "data" / "documents"
    eval_path: Path = PROJECT_ROOT / "data" / "eval" / "questions.json"
    employees_path: Path = PROJECT_ROOT / "data" / "hr" / "employees.json"
    lakehouse_dir: Path = PROJECT_ROOT / "data" / "lakehouse"
    lakehouse_backend: str = "databricks"
    databricks_profile: str = "dbc-a6df516d-a455"
    databricks_warehouse_id: str = "5cd458306322a115"
    databricks_catalog: str = "knowledge_assistant"
    chunk_size: int = 1000
    chunk_overlap: int = 100
    top_k: int = 3
    candidate_k: int = 10


settings = Settings()
