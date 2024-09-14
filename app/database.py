from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings, Base 


# Database connection details (replace with your own)
DATABASE_URL = f"{settings.database.db_driver}:///./{settings.database.db_name}"
# DATABASE_URL = 'postgresql://user:password@host:port/database_name'  # Example for PostgreSQL

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create a session maker bound to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create the database tables
Base.metadata.create_all(bind=engine)

def get_db():
    """
    Function to create a new database session.

    Returns:
        A new database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create all tables in the database (optional)
# Base.metadata.create_all(engine)  # Uncomment to create tables on first run