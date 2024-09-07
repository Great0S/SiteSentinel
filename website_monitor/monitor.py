import asyncio
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

import requests

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
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

websites = {}


def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as file:
            return json.load(file)
    return {}


def save_metadata(metadata):
    with open(METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=4)


def update_metadata(website, screenshot_path):
    metadata = load_metadata()
    metadata[website] = {
        "last_captured": time.time(),
        "screenshot_path": screenshot_path,
    }
    save_metadata(metadata)


def get_website_ip(website_url):
    try:
        return socket.gethostbyname(website_url)
    except (socket.error, socket.gaierror):
        return "IP Not Found"


def capture_screenshot(website_url, output_folder="static/screenshots", delay=3):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    metadata = load_metadata()
    options = {"headless": True, "args": ["--no-sandbox", "--disable-gpu"]}

    with sync_playwright() as p:

        try:
            screenshot_filename = (
                f"{website_url.replace('https://', '').replace('/', '_')}.png"
            )
            screenshot_path = os.path.join(output_folder, screenshot_filename)

            if not os.path.exists(screenshot_path):
                browser = p.chromium.launch(**options)
                page = browser.new_page()
                page.goto(website_url)
                page.screenshot(path=screenshot_path)
                logging.info(f"Screenshot saved for {website_url}")
                update_metadata(website_url, screenshot_path)
                browser.close()
            else:
                logging.info(f"Screenshot already exists for {website_url}")
        except Exception as e:
            logging.error(f"Error capturing screenshot for {website_url}: {e}")
        finally:            
            return screenshot_filename


def add_screenshot_to_website(website):
    global websites
    try:
        last_captured = websites[website].get("last_captured")
        website_ip = websites[website].get("ip")
        if website_ip == "IP Not Found":
            return
        if (
            last_captured is None or (time.time() - last_captured) > 3600
        ):  # Check if more than an hour has passed
            screenshot_path = capture_screenshot(website)
            websites[website]["screenshot"] = screenshot_path
    except Exception as e:
        logging.error(f"Error adding screenshot for {website}: {e}")


def load_websites_from_excel(file_path: str = "website_monitor\\domainler.xlsx"):
    global websites
    try:
        df = pd.read_excel(file_path)
        df["Domain"] = (
            df["Domain"].str.strip().str.lower()
        )  # Remove leading/trailing whitespace and convert to lowercase
        metadata = load_metadata()

        for url in df["Domain"].dropna():
            website = f"https://www.{url}/"
            ip_address = get_website_ip(url)
            websites[website] = {
                "ip": ip_address,
                "status": "Unknown",
                "error_count": 0,
                "status_code": 0,
                "last_captured": metadata.get(website, {}).get("last_captured"),
            }
            scr_thread = Thread(
                target=add_screenshot_to_website, args=(website,))
            scr_thread.start()

        logging.info("Websites loaded from Excel")
        return websites
    except Exception as e:
        logging.error(f"Error loading Excel file: {e}")
        return {}


# Load websites from Excel
load_websites_from_excel()


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
            with requests.get(url, timeout=30) as response:
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


def check_websites():

    for website in websites:

        web_thread = Thread(target=check_website, args=(website,))
        web_thread.start()


def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        check_websites()
        time.sleep(interval)
