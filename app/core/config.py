from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "Patent Mailroom Assistant"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://patent_mailroom:patent_mailroom@localhost:5432/patent_mailroom"

settings = Settings()
