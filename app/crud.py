from sqlalchemy.orm import Session
from app.models import Website

def create_website(db: Session, website_data: dict):
    """Create a new website entry in the database."""
    website = Website(**website_data)
    db.add(website)
    db.commit()
    db.refresh(website)
    return website

def get_websites(db: Session, skip: int = 0, limit: int = 10):
    """Retrieve websites from the database."""
    return db.query(Website).offset(skip).limit(limit).all()

def get_website(db: Session, website_id: int):
    """Retrieve a specific website by ID."""
    return db.query(Website).filter(Website.id == website_id).first()