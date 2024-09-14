from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


Base = declarative_base()

# Define the WebsiteMetadata model
class AddWebsiteRequest(BaseModel):
    url: HttpUrl
    ip: str
    status: str
    status_code: int
    headers: str  # Consider using JSON type for complex structures
    dns_resolution_time: float
    ssl_issued_to: str
    ssl_issuer: List[str]
    ssl_valid_from: Optional[datetime] = None
    ssl_valid_until: Optional[datetime] = None

class WebsiteMetadata(AddWebsiteRequest):
    id: int
    created_at: datetime

class Website(Base):
    __tablename__  = 'websites'
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    ip = Column(String)
    status = Column(String)
    status_code = Column(Integer)
    headers = Column(String)  # Consider using JSON type for complex structures
    dns_resolution_time = Column(Float)
    ssl_issued_to = Column(String)
    ssl_issuer = Column(String)  # Store as a comma-separated string or JSON
    ssl_valid_from = Column(DateTime)
    ssl_valid_until = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())