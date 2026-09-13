"""
InsightAgent Configuration.
Loads environment settings with sensible fallbacks for development, testing, and mock runs.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "InsightAgent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8010

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # InsightFlow Intelligence Engine
    INSIGHTFLOW_API_URL: str = "http://localhost:8000"
    INSIGHTFLOW_AGENT_KEY: str = "insightflow-agent-secret-key"
    INSIGHTFLOW_TIMEOUT_SECONDS: float = 25.0

    # Notion
    NOTION_API_KEY: str = ""
    NOTION_PAGE_ID: str = ""

    # GitHub
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = "SudarshanaWijerathna/insightflow"

    # Slack
    SLACK_WEBHOOK_URL: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_DEFAULT_CHANNEL: str = "#general"

    # Mock Mode: when True, simulates Notion/GitHub/Slack APIs if tokens are not configured
    MOCK_INTEGRATIONS_IF_UNCONFIGURED: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
