from pydantic_settings import BaseSettings,SettingsConfigDict
#BaseSettings: This is a special Pydantic class designed for application settings/configuration.


# settings: defines what configuration the app needs
class Settings(BaseSettings):
    DATABASE_URL: str #gives your application the database URL , the model config points the location of the file annd the extra ignores any other feild in the .env file that is not defined in the settings.
    model_config = SettingsConfigDict(
        env_file="src/.env",
        extra="ignore"
        )
   

# creates the actual settings object
Config = Settings()

# reads your database's secret address out of a file and keeps it stored safely.