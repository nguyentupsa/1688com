import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Google AI
    google_model: str = "gemini-2.5-flash"
    google_api_key: Optional[str] = None

    # Negotiation Defaults
    default_max_turns: int = 6
    default_timeout_seconds: int = 300
    default_language: str = "zh"

    # Playwright
    browser_headless: bool = False
    browser_slowmo: int = 100
    user_data_dir: str = "./data/user_data_dir"

    # Data Paths
    data_dir: str = "./data"

    # Login URL (exact as specified in system prompt)
    login_url: str = (
        "https://login.taobao.com/?redirect_url=https%3A%2F%2Flogin.1688.com%2Fmember%2Fjump.htm"
        "%3Ftarget%3Dhttps%253A%252F%252Flogin.1688.com%252Fmember%252FmarketSigninJump.htm"
        "%253FDone%253Dhttps%25253A%25252F%25252Fwork.1688.com%25252Fhome%25252Fseller.htm"
        "%25253Fspm%25253Da261p.11773258.topmenu.dsellercenterentry&style=tao_custom&from=1688web"
    )

    # Expected post-login URL
    work_1688_url_pattern: str = "https://work.1688.com/home/"

    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()