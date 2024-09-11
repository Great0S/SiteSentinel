import pathlib
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.website_monitor.monitor import load_websites_from_excel

app = FastAPI()
BASE_DIR = pathlib.Path(__file__).parent
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def home():
    return {"message": "First FastAPI app"}

@app.get("/websites", response_class=HTMLResponse)
async  def websites_data(request: Request):
    websites = await load_websites_from_excel()
    return templates.TemplateResponse("websites.html", {"request": request, "websites": websites})