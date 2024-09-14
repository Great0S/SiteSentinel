from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from app import app, settings, logger, authenticate_user, get_user, fake_users_db, load_websites_from_excel, create_website, get_website, get_websites, templates, get_db, WebsiteMetadata



@app.get("/")
def home():
    logger.info("Home endpoint accessed")
    return {"message": "First FastAPI app with SQLAlchemy!"}



@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": user.username, "token_type": "bearer"}



@app.get("/users/me")
async def read_users_me(token: str = Depends(settings.oauth2_scheme)):
    user = get_user(fake_users_db, token)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user



@app.get("/websites", response_class=HTMLResponse)
async def websites_data(request: Request):
    websites = await load_websites_from_excel()
    return templates.TemplateResponse("websites.html", {"request": request, "websites": websites})



@app.post("/websites", response_model=WebsiteMetadata)
def add_website(website_data: dict, db: Session = Depends(get_db)):
    """Add a new website."""
    website = create_website(db=db, website_data=website_data)
    logger.info(f"Website added: {website.url}")
    return website

@app.get("/websites/{website_id}")
def read_website(website_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific website by ID."""
    website = get_website(db=db, website_id=website_id)
    if website is None:
        raise HTTPException(status_code=404, detail="Website not found")
    return website


@app.get("/websites/raw", response_model=list[WebsiteMetadata])
async def read_websites(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Retrieve a list of websites."""
    websites = get_websites(db, skip=skip, limit=limit)
    return websites


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": "Custom error message"}
    )
