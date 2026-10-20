import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    GEMINI_API_KEY: str
    ADMIN_ID: int
    
    PRIMARY_MODEL: str = "gemini-3.5-flash"
    FALLBACK_MODEL: str = "gemini-3.1-flash-lite"
    
    DB_PATH: str = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "database.db"))
    TEMP_DIR: str = os.getenv("TEMP_DIR", os.path.join(os.path.dirname(__file__), "temp"))

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
