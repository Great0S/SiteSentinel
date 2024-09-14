import asyncio
import re
import sys
import pandas as pd
import smtplib
import os
import time
from playwright.async_api import async_playwright
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import logger, settings
from app.utils import enrich_metadata

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Constants
ERROR_THRESHOLD = 3
RETRY_COUNT = 3


# Global variables
websites = {}

def load_metadata():
    if os.path.exists(settings.metadata_file):
        try:
            df = pd.read_excel(settings.metadata_file, engine="openpyxl")
            if not df.empty:  # Check if the file is not empty
                df = df.replace({float('nan'): None})
                return df.set_index('domain').T.to_dict()  # Convert to dictionary
            else:
                return {}
        except Exception as e:
            # Handle file read errors
            print(f"Error reading Excel file {settings.metadata_file}: {e}")
            return {}
    return {}

def save_metadata(metadata):
    try:
         # Convert dictionary to DataFrame with 'domain' as a column
        df = pd.DataFrame.from_dict(metadata, orient='index')
        df.index.name = 'domain'  # Set 'domain' as index to move it to a column
        df.reset_index(inplace=True)  # Convert the index (domain) back to a normal column
        
        # Save the DataFrame back to an Excel file
        df.to_excel(settings.metadata_file, index=False, engine="openpyxl")
    except Exception as e:
        print(f"Error writing Excel file {settings.metadata_file}: {e}")


def update_metadata(website, screenshot_name):
    logger.info(f"Updating metadata for {website}")
    metadata = load_metadata()
    data = {
            "last_captured": time.time(),
            "screenshot_path": screenshot_name,}
    if metadata:
        metadata['domain'][website] = data
        save_metadata(metadata)
    else:
        save_metadata({website: data})


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def get_website_screenshot(website_url, output_folder="app/static/screenshots"):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    async with async_playwright() as p:
        try:
            logger.info(f"Capturing screenshot for {website_url}")
            screenshot_filename = f"{website_url.replace('https://', '').replace('/', '_')}.png"
            screenshot_path = os.path.join(output_folder, screenshot_filename)

            options = {"headless": True, "slow_mo": 0}
            browser = await p.chromium.launch(**options)
            page = await browser.new_page()
            await page.goto(website_url, wait_until="load")
            await page.screenshot(path=screenshot_path) 
            await browser.close()
            logger.info(f"Screenshot captured for {website_url}")
            return screenshot_filename

        except Exception as e:
            logger.error(f"Error capturing screenshot for {website_url}: {e}")
            raise  # Raise the exception to trigger the retry


def add_screenshot_to_website(url):
    global metadata
    try:
        last_captured = metadata[url].get("last_captured")
        current_time = time.time()
        website = f"https://www.{url}/"
    
        if last_captured is None or last_captured + 7200 <= current_time:  # Check if more than an hour has passed
            
            screenshot_filename = asyncio.run(get_website_screenshot(website))
            if screenshot_filename:
                metadata[url]["screenshot"] = screenshot_filename
                metadata[url]["last_captured"] = time.time()
                logger.info(f"Screenshot added for {url}: {screenshot_filename}")
            else:
                logger.warning(f"Screenshot capture failed for {url}. No file returned.")
        else:
            logger.info(f"Screenshot already exists for {url}, last captured at {last_captured}")

    except Exception as e:
        logger.error(f"Error adding screenshot for {url}: {e}")

async def load_websites_from_excel():
    global metadata
    try:

        logger.warning("Loading websites from Excel")
        metadata = load_metadata()
        loop = asyncio.get_event_loop()

        if not metadata:
            logger.warning("No websites found in metadata")
            return {}
        
        tasks = [enrich_metadata(url, metadata) for url, _ in metadata.items()]   
        results = await asyncio.gather(*tasks)
        pass
        
        website_state = {website: data for x in results for website, data in x.items()}
        
        with ThreadPoolExecutor(max_workers=20) as executor:  # Limit to 20 concurrent threads
            for url, data in website_state.items():
                
                website = re.sub(r"https://www.|/", "", url)              
                metadata[website].update(data)
                
                if metadata[website]["ip"] == "IP Not Found":
                    continue

                screenshot_future = loop.run_in_executor(executor, add_screenshot_to_website, website)
                await screenshot_future
                
        if metadata:
            save_metadata(metadata)
        logger.info("Websites loaded from Excel successfully")
        return metadata
    except Exception as e:
        logger.error(f"Error loading Excel file: {e}")
        return {}

def send_email_alert(website):
    try:
        logger.info(f"Sending email alert for {website}")
        with smtplib.SMTP_SSL(settings.email_server, settings.email_port) as server:
            server.login(settings.email_sender, settings.email_password)
            subject = f"Website Down Alert: {website}"
            body = f"ALERT: The website {website} is down for {ERROR_THRESHOLD} consecutive checks."
            message = f"Subject: {subject}\n\n{body}"
            server.sendmail(settings.email_sender, settings.email_receiver, message)
            logger.info(f"Email alert sent for {website}")
    except Exception as e:
        logger.error(f"Failed to send email for {website}. Exception: {e}")

async def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        logger.debug("Starting periodic monitoring")
        await load_websites_from_excel()
        logger.info("Periodic monitoring completed")
        time.sleep(interval)
