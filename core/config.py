from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "smartdesk"
    mongo_test_db: str = "smartdesk_test"
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    token_expire_minutes: int = Field(default=30, gt=0)


settings = Settings()
