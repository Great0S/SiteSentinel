from fastapi import FastAPI, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import datetime

from db.models.website_data import Website
from db.database import get_db

app = FastAPI()


@app.get("/websites", response_model=list[Website])
def get_websites(db: Session = Depends(get_db)):
    """
    Retrieves a list of all websites from the database.
    """
    websites = db.query(Website).all()
    return websites


@app.post("/websites", response_model=Website)
def create_website(website: Website, db: Session = Depends(get_db)):
    """
    Creates a new website in the database.
    """
    website.last_captured = datetime.now()  # Update capture timestamp
    db.add(website)
    db.commit()
    db.refresh(website)
    return website


@app.get("/websites/{website_id}", response_model=Website)
def get_website(website_id: int, db: Session = Depends(get_db)):
    """
    Retrieves a specific website by ID.
    """
    website = db.query(Website).filter(Website.id == website_id).first()
    if not website:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@app.put("/websites/{website_id}", response_model=Website)
def update_website(website_id: int, website_data: Website = Body(...), db: Session = Depends(get_db)):
    """
    Updates a specific website in the database.
    """
    db_website = db.query(Website).filter(Website.id == website_id).first()
    if not db_website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Update specific fields (customize as needed)
    db_website.url = website_data.url
    db_website.ip_address = website_data.ip_address
    db_website.status = website_data.status
    db_website.error_count = website_data.error_count
    db_website.status_code = website_data.status_code

    # Update capture timestamp for partial updates
    db_website.last_captured = datetime.now()

    db.commit()
    db.refresh(db_website)
    return db_website


@app.delete("/websites/{website_id}")
def delete_website(website_id: int, db: Session = Depends(get_db)):
    """
    Deletes a specific website from the database.
    """
    db_website = db.query(Website).filter(Website.id == website_id).first()
    if not db_website:
        raise HTTPException(status_code=404, detail="Website not found")
    db.delete(db_website)
    db.commit()
    return {"message": "Website deleted successfully"}