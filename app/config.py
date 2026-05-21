from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    hardware_api_url: str
    database_url: str
    llm_api_key: str
    app_env: str = "development"
    debug: bool = True
    use_test_date: bool = False
    test_start_date: str = ""
    test_end_date: str = ""

settings = Settings()