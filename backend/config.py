import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    elasticsearch_host: str = os.getenv("ELASTICSEARCH_HOST", "localhost")
    elasticsearch_port: int = int(os.getenv("ELASTICSEARCH_PORT", "9200"))
    elasticsearch_username: str = os.getenv("ELASTICSEARCH_USERNAME", "elastic")
    elasticsearch_password: str = os.getenv("ELASTICSEARCH_PASSWORD", "changeme")
    elasticsearch_scheme: str = os.getenv("ELASTICSEARCH_SCHEME", "http")

    @property
    def es_url(self) -> str:
        return (
            f"{self.elasticsearch_scheme}://"
            f"{self.elasticsearch_username}:{self.elasticsearch_password}"
            f"@{self.elasticsearch_host}:{self.elasticsearch_port}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
