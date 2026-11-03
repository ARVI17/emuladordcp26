from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Asistente FC 26"
    database_url: str = "postgresql+psycopg://fc26:fc26_local_change_me@database:5432/fc26"
    database_pool_size: int = 3
    database_max_overflow: int = 2
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_keep_alive: str = "2m"
    cors_origins: str = "http://localhost:8080,http://127.0.0.1:8080"
    max_upload_mb: int = 10
    adb_enabled: bool = True
    adb_path: str = "adb"
    adb_default_address: str = "host.docker.internal:5555"
    seed_demo: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
