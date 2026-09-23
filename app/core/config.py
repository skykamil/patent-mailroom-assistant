from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Patent Mailroom Assistant"
    environment: str = "development"

settings = Settings()
