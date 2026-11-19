"""Configuration module for the HR/IT Helpdesk AI Agent."""

import os
from pathlib import Path
from dataclasses import dataclass

# Attempt loading environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Attempt loading from Streamlit secrets (Streamlit Community Cloud support)
try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, (str, int, float, bool)) and k not in os.environ:
                os.environ[k] = str(v)
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    # Directory paths
    base_dir: Path = BASE_DIR
    data_dir: Path = BASE_DIR / "data"
    db_dir: Path = BASE_DIR / "db"
    hr_policy_path: Path = BASE_DIR / "data" / "hr_policy.md"
    it_policy_path: Path = BASE_DIR / "data" / "it_policy.md"
    init_sql_path: Path = BASE_DIR / "db" / "init.sql"
    chroma_dir: Path = BASE_DIR / "data" / "chroma_db"

    # API Keys
    gemini_api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    openai_api_key: str = os.getenv("OPENAI_API_KEY") or ""
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY") or ""

    # Model configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "").lower()
    llm_model: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # Database configuration
    db_host: str = os.getenv("DB_HOST", "localhost")
    db_port: int = int(os.getenv("DB_PORT", "5432"))
    db_name: str = os.getenv("DB_NAME", "hr_it_helpdesk")
    db_user: str = os.getenv("DB_USER", "helpdesk_user")
    db_password: str = os.getenv("DB_PASSWORD", "helpdesk_pass")

    @property
    def postgres_connection_string(self) -> str:
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def active_llm_provider(self) -> str:
        """Determine which LLM provider to use based on available keys and settings."""
        if self.llm_provider:
            return self.llm_provider
        if self.gemini_api_key:
            return "gemini"
        if self.openai_api_key:
            return "openai"
        if self.anthropic_api_key:
            return "anthropic"
        return "mock"

settings = Settings()
