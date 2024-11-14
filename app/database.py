import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings, Base 


# Database connection details (replace with your own)
DATABASE_URL = f"{settings.database.db_driver}://{settings.database.db_user}:{settings.database.db_password}@{settings.database.db_host}:{settings.database.db_port}/{settings.database.db_name}"
# DATABASE_URL = 'postgresql://user:password@host:port/database_name'  # Example for PostgreSQL

# Create the database engine
engine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create a session maker bound to the engine
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession)

async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Drop all tables
        await conn.run_sync(Base.metadata.create_all)  # Create all tables

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session