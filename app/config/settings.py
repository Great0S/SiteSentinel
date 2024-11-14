# app/config/settings.py

from fastapi.security import OAuth2PasswordBearer
from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    
    db_driver: str = "postgresql+asyncpg"
    db_host: str = Field(..., env="DB_HOST")
    db_port: str = Field(..., env="DB_PORT")
    db_name: str = Field(..., env="DB_NAME")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")

class Settings(BaseSettings):
    app_name: str = "Site Sentinel App"
    database: DatabaseSettings = DatabaseSettings()
    database_url: str = f"{database.db_driver}://{database.db_user}:{database.db_password}@{database.db_host}:{database.db_port}/{database.db_name}"
    
    # Initialize the OAuth2 scheme
    oauth2_scheme: OAuth2PasswordBearer = OAuth2PasswordBearer(tokenUrl="token")

    # Email settings
    email_server: str = Field(..., env="EMAIL_SERVER")
    email_port: str = Field(..., env="EMAIL_PORT")
    email_sender: str = Field(..., env="EMAIL_SENDER")
    email_password: str = Field(..., env="EMAIL_PASSWORD")
    email_receiver: str = Field(..., env="EMAIL_RECEIVER")

    # IPInfo settings
    ipinfo_token: str = Field(..., env="IPINFO_TOKEN")

    # Metadata file path
    metadata_file: str = Field(default="app/website_monitor/domainler.xlsx", env="METADATA_FILE")


    class Config:
        env_file = ".env"  # Specify the .env file to load environment variables from
        extra = 'allow'  # Allow extra fields in the settings
