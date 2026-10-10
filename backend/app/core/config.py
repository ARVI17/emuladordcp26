from functools import lru_cache
from urllib.parse import quote
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Club Lab · FC 27"
    database_url: str = ""
    postgres_db: str = "fc26"
    postgres_user: str = "fc26"
    postgres_password: str = "fc26_local_change_me"
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
    seed_demo: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def default_database_url(self):
        if not self.database_url:
            self.database_url = "postgresql+psycopg://{}:{}@database:5432/{}".format(
                quote(self.postgres_user, safe=""), quote(self.postgres_password, safe=""), quote(self.postgres_db, safe="")
            )
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings: return Settings()
settings = get_settings()
