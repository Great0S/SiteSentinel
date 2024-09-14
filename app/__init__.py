from contextlib import asynccontextmanager
import pathlib

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .config import Settings, logger
from .models.auth import authenticate_user, get_user, fake_users_db
from .models.website_data import WebsiteMetadata
from .database import get_db
from .crud import create_website, get_website, get_websites
from .website_monitor import load_websites_from_excel

    
__all__ = [
    "Settings",
    "logger",
    "authenticate_user",
    "get_user",
    "fake_users_db",
    "WebsiteMetadata",
    "create_website",
    "get_db",
    "get_website",
    "get_websites",
    "load_websites_from_excel"
]

# Load settings
settings = Settings()

# Create Fast API instance
app = FastAPI()


BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
