import asyncio
from concurrent.futures import ThreadPoolExecutor
import sys
import pandas as pd
import aiohttp
import smtplib
import logging
import os
import json
import socket
import time
from playwright.sync_api import sync_playwright
from threading import Thread
from rich.logging import RichHandler
import requests
from playwright.async_api import async_playwright

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Constants
EMAIL_SERVER = os.getenv("EMAIL_SERVER")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
ERROR_THRESHOLD = 3
RETRY_COUNT = 3
METADATA_FILE = "metadata.json"

# Logging configuration
logging.basicConfig(
    handlers=[RichHandler()],
    level=logging.INFO, 
    format="%(asctime)s - %(levelname)s - %(message)s")

# Global variables
websites = {}

def load_metadata():
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, "r") as file:
                content = file.read()
                if content.strip():  # Check if the file is not empty
                    return json.loads(content)
                else:
                    return {}
        except json.JSONDecodeError as e:
            # Handle JSON decode errors (e.g., empty or invalid JSON)
            print(f"Error decoding JSON from file {METADATA_FILE}: {e}")
            return {}
    return {}

def save_metadata(metadata):
    with open(METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=4)


def update_metadata(website, screenshot_name):
    metadata = load_metadata()
    data = {
            "last_captured": time.time(),
            "screenshot_path": screenshot_name,}
    if metadata:
        metadata[website] = data
        save_metadata(metadata)
    else:
        save_metadata({website: data})


def get_website_ip(website_url):
    try:
        return socket.gethostbyname(website_url)
    except (socket.error, socket.gaierror):
        return "IP Not Found"


async def get_website_screenshot(website_url, output_folder="app/static/screenshots"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    async with async_playwright() as p:

        try:
            screenshot_filename = f"{website_url.replace('https://', '').replace('/', '_')}.png"
            screenshot_path = os.path.join(output_folder, screenshot_filename)

            options = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}
            browser = await p.chromium.launch(**options)
            page = await browser.new_page()
            await page.goto(website_url, wait_until="networkidle")
            await page.screenshot(path=screenshot_path) 
            await browser.close()

            update_metadata(website_url, screenshot_filename)
            return screenshot_filename

        except Exception as e:
            logging.error(f"Error capturing screenshot for {website_url}: {e}")

async def add_screenshot_to_website(website):
    global websites
    try:
        last_captured = websites[website].get("last_captured")
        website_ip = websites[website].get("ip")
        current_time = time.time()

        if website_ip == "IP Not Found":
            return
    
        if last_captured is None or last_captured + 3600 <= current_time:  # Check if more than an hour has passed
            
            screenshot_filename = await get_website_screenshot(website)
            websites[website]["screenshot"] = screenshot_filename
            websites[website]["last_captured"] = time.time()
            logging.info(f"Screenshot added for {website}")
        else:
            logging.info(f"Screenshot already exists for {website}")
    except Exception as e:
        logging.error(f"Error adding screenshot for {website}: {e}")


async def load_websites_from_excel(file_path: str = "app\\website_monitor\\domainler.xlsx"):
    global websites
    try:
        df = pd.read_excel(file_path, engine="openpyxl")
        df["Domain"] = df["Domain"].str.strip().str.lower()  # Remove leading/trailing whitespace and convert to lowercase
        metadata = load_metadata()
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=15) as executor:  # Limit to 5 concurrent threads
            for url in df["Domain"].dropna():
                website = f"https://www.{url}/"
                ip_address = await loop.run_in_executor(executor, get_website_ip, url)
                websites[website] = {
                    "ip": ip_address,
                    "status": "Unknown",
                    "error_count": 0,
                    "status_code": 0,
                    "last_captured": metadata.get(website, {}).get("last_captured"),
                    "screenshot": metadata.get(website, {}).get("screenshot_path"),
                }
                

                if loop.is_running():
                    # Offload blocking work to a thread pool to avoid blocking the event loop
                    loop.run_in_executor(executor, lambda: asyncio.run(add_screenshot_to_website(website)))
                else:
                    asyncio.run(add_screenshot_to_website(website))

                metadata = load_metadata()
                

        logging.info("Websites loaded from Excel")
        return websites
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return {}

def send_email_alert(website):
    try:
        with smtplib.SMTP_SSL(EMAIL_SERVER, EMAIL_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            subject = f"Website Down Alert: {website}"
            body = f"ALERT: The website {website} is down for {
                ERROR_THRESHOLD} consecutive checks."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message)
            logging.info(f"Email alert sent for {website}")
    except Exception as e:
        logging.error(f"Failed to send email for {website}. Exception: {e}")


def check_website(url):
    global websites
    for _ in range(RETRY_COUNT + 1):
        try:
            with requests.get(url, timeout=30, stream=True) as response:
                
                websites[url]["status_code"] = response.status_code
                if response.status_code == 200:
                    websites[url]["status"] = "Up"
                    websites[url]["error_count"] = 0  # Reset error count
                    logging.info(f"Website is available: {url}")
                    return True
                else:
                    logging.warning(
                        f"Error: {url} returned status code {
                            response.status_code}"
                    )
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Error: {url} is not reachable. Exception: {e}")

    websites[url]["error_count"] += 1  # Increment error count
    if websites[url]["error_count"] >= ERROR_THRESHOLD:
        websites[url]["status"] = "Down"
    else:
        websites[url]["status"] = "Error"
        # send_email_alert(url)

    logging.error(
        f"{url} has been down for {
            websites[url]['error_count']} consecutive checks"
    )
    return False


async def check_websites():
    global websites
    
    # Load websites from Excel
    await load_websites_from_excel()
    for website in websites:

        web_thread = Thread(target=check_website, args=(website,))
        web_thread.start()
    
    return websites

async def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        await check_websites()
        time.sleep(interval)
