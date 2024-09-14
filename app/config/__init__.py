# app/config/__init__.py

"""
Configuration module for the FastAPI application.
"""

from .settings import Settings  # Import settings
from .logger import logger  # Import logger
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
settings = Settings()