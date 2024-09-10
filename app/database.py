from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models import Base  # Replace with the path to your models file

# Database connection details (replace with your own)
DATABASE_URL = 'sqlite:///websites.db'  #Sqllite
# DATABASE_URL = 'postgresql://user:password@host:port/database_name'  # Example for PostgreSQL

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create a session maker bound to the engine
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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