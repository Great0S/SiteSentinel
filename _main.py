import asyncio
import logging
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from weasyprint import CSS, HTML
from website_monitor.monitor import check_websites
import io

# Initialize FastAPI app
app = FastAPI()

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Basic logging configuration
logging.basicConfig(
    level=logging.INFO,  # Set log level to INFO
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]  # Simple console logging
)
connected_clients = []
# Start the async monitoring
async def start_periodic_monitoring():
    while True:
        try:
            # Periodically emit website status updates to connected clients
            websites = await check_websites()
            for client in connected_clients:
                await client.send_json(websites)
            await asyncio.sleep(500)  # Adjust the sleep interval as per your requirement
        except Exception as e:
            logging.error(f"Error in monitoring: {e}")

# Start async monitoring in an event loop

async def startup_event():
    asyncio.create_task(start_periodic_monitoring())

app.add_event_handler("startup", startup_event)

# Route for the index page
@app.get("/")
async def index(request: Request):
    try:
        websites = await check_websites()  # Ensure you have up-to-date data
        return templates.TemplateResponse("index.html", {"request": request, "websites": websites})
    except Exception as e:
        logging.error(f"Error in index route: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")

@app.get("/export_pdf")
async def export_pdf():
    try:
        websites = await check_websites()  # Ensure you have up-to-date data
        html = templates.get_template("index.html").render(websites=websites)
        css = CSS(string='@page { size: A4; margin: 0.5cm; }')
        pdf = HTML(string=html).write_pdf(stylesheets=[css])

        # Create a StreamingResponse to send the PDF file
        return StreamingResponse(io.BytesIO(pdf), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=website_status.pdf"})
    except Exception as e:
        logging.error(f"Error in export_pdf route: {e}")
        raise HTTPException(status_code=500, detail="An error occurred")

# WebSocket route for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  

    connected_clients.append(websocket)

    try:
        while True:  

            # Push updates to the connected client
            websites = await check_websites()
            await websocket.send_json(websites)
            await asyncio.sleep(500)  # Adjust the interval as needed
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        connected_clients.remove(websocket)
        await websocket.close()

# Run the application
if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.create_task(start_periodic_monitoring())
    uvicorn.run(app, host="0.0.0.0", port=8000)
