# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    hardware_api_url: str
    database_url: str
    llm_api_key: str
    app_env: str = "development"
    debug: bool = True

settings = Settings()