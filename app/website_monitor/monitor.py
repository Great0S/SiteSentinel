import asyncio
import sys
import pandas as pd
import aiohttp
import smtplib
import logging
import os
import time
from rich.logging import RichHandler
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor

from app.utils import enrich_metadata

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
METADATA_FILE = "app/website_monitor/domainler.xlsx"

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
            df = pd.read_excel(METADATA_FILE, engine="openpyxl")
            if not df.empty:  # Check if the file is not empty
                df = df.replace({float('nan'): None})
                return df.set_index('domain').T.to_dict()  # Convert to dictionary
            else:
                return {}
        except Exception as e:
            # Handle file read errors
            print(f"Error reading Excel file {METADATA_FILE}: {e}")
            return {}
    return {}

def save_metadata(metadata):
    try:
         # Convert dictionary to DataFrame with 'domain' as a column
        df = pd.DataFrame.from_dict(metadata, orient='index')
        df.index.name = 'domain'  # Set 'domain' as index to move it to a column
        df.reset_index(inplace=True)  # Convert the index (domain) back to a normal column
        
        # Save the DataFrame back to an Excel file
        df.to_excel(METADATA_FILE, index=False, engine="openpyxl")
    except Exception as e:
        print(f"Error writing Excel file {METADATA_FILE}: {e}")


def update_metadata(website, screenshot_name):
    logging.info(f"Updating metadata for {website}")
    metadata = load_metadata()
    data = {
            "last_captured": time.time(),
            "screenshot_path": screenshot_name,}
    if metadata:
        metadata['domain'][website] = data
        save_metadata(metadata)
    else:
        save_metadata({website: data})


async def get_website_screenshot(website_url, output_folder="app/static/screenshots"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    async with async_playwright() as p:

        try:
            screenshot_filename = f"{website_url.replace('https://', '').replace('/', '_')}.png"
            screenshot_path = os.path.join(output_folder, screenshot_filename)

            options = {"headless": True, "slow_mo": 0}
            browser = await p.chromium.launch(**options)
            page = await browser.new_page()
            await page.goto(website_url, wait_until="load")
            await page.screenshot(path=screenshot_path) 
            await browser.close()

            return screenshot_filename

        except Exception as e:
            if e.name == "TimeoutError":
                logging.error(f"Capturing screenshot for {website_url} Timed out")
                return None
            else:
                logging.error(f"Error capturing screenshot for {website_url}: {e}")

def add_screenshot_to_website(url):
    global metadata
    try:
        last_captured = metadata[url].get("last_captured")
        current_time = time.time()
        website = f"https://www.{url}/"
    
        if last_captured is None or last_captured + 3600 <= current_time:  # Check if more than an hour has passed
            
            screenshot_filename = asyncio.run(get_website_screenshot(website))
            time_taken = current_time - time.time()
            logging.info(f"get_website_screenshot function time taken {time_taken:.2f}")
            metadata[url]["screenshot"] = screenshot_filename
            metadata[url]["last_captured"] = time.time()
            logging.info(f"Screenshot added for {url}")

        else:
            logging.info(f"Screenshot already exists for {url}")
    except Exception as e:
        logging.error(f"Error adding screenshot for {url}: {e}")

async def load_websites_from_excel():
    global metadata
    try:
        # df = pd.read_excel(file_path, engine="openpyxl")
        # df["Domain"] = df["Domain"].str.strip().str.lower()  # Remove leading/trailing whitespace and convert to lowercase
        metadata = load_metadata()
        loop = asyncio.get_event_loop()

        
        tasks = [enrich_metadata(url) for url, _ in metadata.items()]   
        results = await asyncio.gather(*tasks)
        
        website_state = {website: {"ip": ip, "status": status, "status_code": status_code} for website, ip, status, status_code in results}
        
        with ThreadPoolExecutor(max_workers=20) as executor:  # Limit to 20 concurrent threads
            for url, data in metadata.items():
                
                website = f"https://www.{url}/"                
                metadata[url] = {
                    "ip": website_state[website]["ip"],
                    "status": website_state[website]["status"],
                    "status_code": website_state[website]["status_code"],
                    "last_captured": data.get("last_captured", None),
                    "screenshot": data.get("screenshot", None),
                }
                
                if metadata[url]["ip"] == "IP Not Found":
                    continue

                screenshot_future = loop.run_in_executor(executor, add_screenshot_to_website, url)
                await screenshot_future
                
        if metadata:
            save_metadata(metadata)
        logging.info("Websites loaded from Excel")
        return metadata
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return {}

def send_email_alert(website):
    try:
        with smtplib.SMTP_SSL(EMAIL_SERVER, EMAIL_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            subject = f"Website Down Alert: {website}"
            body = f"ALERT: The website {website} is down for {ERROR_THRESHOLD} consecutive checks."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, message)
            logging.info(f"Email alert sent for {website}")
    except Exception as e:
        logging.error(f"Failed to send email for {website}. Exception: {e}")

async def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        logging.info("Periodic monitoring started")
        start = time.time()
        await load_websites_from_excel()
        taken = time.time() - start
        logging.info(f"Periodic monitoring time taken {taken:.2f}")
        time.sleep(interval)
