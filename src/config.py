import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# settings: defines what configuration the app needs
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    model_config = SettingsConfigDict(
        env_file=(".env", "src/.env"),
        extra="ignore"
    )

# creates the actual settings object
Config = Settings()


# reads your database's secret address out of a file and keeps it stored safely.