from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app import app, logger,load_websites_from_excel, create_website, get_website, get_websites, templates, get_db, WebsiteMetadata
from app.database import init_models, get_db
from sqlalchemy.orm import Session

from app.models.website_data import Website


@app.on_event("startup")
async def startup_event():
    await init_models()  # Call the function to create tables


@app.get("/")
def home():
    logger.info("Home endpoint accessed")
    return {"message": "First FastAPI app with SQLAlchemy!"}

# @app.post("/token")
# async def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = await authenticate_user(form_data.username, form_data.password)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     return {"access_token": user.username, "token_type": "bearer"}

# @app.post("/users/")
# async def create_user(name: str, email: str, db: AsyncSession = Depends(get_db)):
#     """Create a new user."""
#     new_user = User(name=name, email=email)
#     async with db.begin():
#         db.add(new_user)
#     return {"name": new_user.name, "email": new_user.email}

# @app.get("/users/")
# async def read_users(db: AsyncSession = Depends(get_db)):
#     """Retrieve all users."""
#     async with db.begin():
#         result = await db.execute(select(User))
#         users = result.scalars().all()
#     return users

@app.get("/websites", response_class=HTMLResponse, response_model=list[Website])
async def websites_data(request: Request, db: Session = Depends(get_db)):
    """
    Retrieves a list of all websites from the database.
    """
    websites = db.query(Website).all()
    websites = await load_websites_from_excel()
    return templates.TemplateResponse("websites.html", {"request": request, "websites": websites})



@app.post("/websites/")
async def add_website(url: str, description: str, db: AsyncSession = Depends(get_db)):
    """Create a new website."""
    new_website = await create_website(db=db, url=url, description=description)
    return {"url": new_website.url, "description": new_website.description}

@app.get("/websites/")
async def read_websites(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Retrieve all websites."""
    websites = await get_websites(db=db, skip=skip, limit=limit)
    return websites

@app.get("/websites/{website_id}")
async def read_website(website_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a specific website by ID."""
    website = await get_website(db=db, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")
    return {"url": website.url, "description": website.description}
    return websites


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": "Custom error message"}
    )
