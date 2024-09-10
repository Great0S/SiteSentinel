import time
from sqlalchemy import Column, Integer, String, DateTime, Text

from db.models import Base


class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)  # Assuming `url` is the website identifier
    ip_address = Column(String)
    status = Column(String)
    error_count = Column(Integer)
    status_code = Column(Integer)
    last_captured = Column(DateTime, default=time.time())  # Store the timestamp
    screenshot_path = Column(Text)  # Store the path to the screenshot