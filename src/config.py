import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# settings: defines what configuration the app needs
class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Cloudinary credentials — set these in .env locally and in Vercel env vars for production
    CLOUDINARY_CLOUD_NAME: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY: str = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET: str = os.getenv("CLOUDINARY_API_SECRET", "")

    model_config = SettingsConfigDict(
        env_file=(".env", "src/.env"),
        extra="ignore"
    )

# creates the actual settings object
Config = Settings()


# reads your database's secret address out of a file and keeps it stored safely.