# app/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Website

async def create_website(db: AsyncSession, url: str, description: str):
    """Create a new website entry in the database."""
    new_website = Website(url=url, description=description)
    async with db.begin():
        db.add(new_website)
    return new_website

async def get_websites(db: AsyncSession, skip: int = 0, limit: int = 10):
    """Retrieve websites from the database."""
    async with db.begin():
        result = await db.execute(select(Website).offset(skip).limit(limit))
        return result.scalars().all()

async def get_website(db: AsyncSession, website_id: int):
    """Retrieve a specific website by ID."""
    async with db.begin():
        result = await db.execute(select(Website).where(Website.id == website_id))
        return result.scalar_one_or_none()
