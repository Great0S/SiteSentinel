from ssl_monitor import SSLMonitor
from health_scoring import EnhancedHealthScorer, HealthScorer
import requests
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
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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

# Historical data storage for enhanced health scoring
performance_history = {}
MAX_HISTORY_ENTRIES = 50  # Keep last 50 measurements per website


def get_historical_data(url: str) -> list:
    """Get historical performance data for a website"""
    return performance_history.get(url, [])


def add_performance_record(url: str, data: dict):
    """Add a performance record to history"""
    if url not in performance_history:
        performance_history[url] = []

    # Add current record
    performance_history[url].append({
        'timestamp': time.time(),
        'response_time': data.get('response_time'),
        'status_code': data.get('status_code'),
        'status': data.get('status'),
        'error_count': data.get('error_count', 0),
        'ssl_info': data.get('ssl_info', {})
    })

    # Keep only recent entries
    if len(performance_history[url]) > MAX_HISTORY_ENTRIES:
        performance_history[url] = performance_history[url][-MAX_HISTORY_ENTRIES:]


def calculate_enhanced_health_score(url: str, current_data: dict) -> dict:
    """Calculate enhanced health score with historical context"""
    try:
        # Get historical data
        historical_data = get_historical_data(url)

        # Use enhanced health scorer
        health_data = EnhancedHealthScorer.calculate_health_score(
            current_data,
            historical_data
        )

        logging.info(
            f"Enhanced health score for {url}: {health_data['score']} "
            f"({health_data['grade']}) with {health_data.get('confidence', 0):.1f}% confidence"
        )

        return health_data

    except Exception as e:
        logging.error(
            f"Error calculating enhanced health score for {url}: {e}")
        # Fallback to basic health scoring
        return HealthScorer.calculate_health_score(current_data)


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
    """Extract domain from URL and get its IP address"""
    try:
        # Extract domain from URL
        from urllib.parse import urlparse
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path.split('/')[0]

        # Remove port if present
        if ':' in domain and not domain.startswith('['):  # Handle IPv6
            domain = domain.split(':')[0]

        # Remove www. if present
        if domain.startswith('www.'):
            domain = domain[4:]

        # Try DNS resolution with timeout
        import socket
        socket.setdefaulttimeout(10)  # 10 second timeout
        ip_address = socket.gethostbyname(domain)
        logging.info(f"Resolved {domain} to {ip_address}")
        return ip_address

    except (socket.error, socket.gaierror) as e:
        logging.error(f"Failed to resolve IP for {website_url}: {e}")
        # Try alternative DNS resolution
        try:
            import dns.resolver
            result = dns.resolver.resolve(domain, 'A')
            if result:
                ip_address = str(result[0])
                logging.info(
                    f"Alternative DNS resolved {domain} to {ip_address}")
                return ip_address
        except:
            pass
        return "Unknown"
    except Exception as e:
        logging.error(f"Unexpected error resolving IP for {website_url}: {e}")
        return "Unknown"
    finally:
        socket.setdefaulttimeout(None)  # Reset timeout


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


def load_websites_from_excel(file_path: str = ""):
    global websites
    try:
        if not file_path:
            logging.warning("No file path provided for Excel loading")
            return {}

        if not os.path.exists(file_path):
            logging.warning(f"Excel file not found: {file_path}")
            return {}

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


# Load websites from Excel only if file exists
DEFAULT_EXCEL_FILE = "websites.xlsx"
if os.path.exists(DEFAULT_EXCEL_FILE):
    load_websites_from_excel(DEFAULT_EXCEL_FILE)
else:
    logging.info(
        "No default Excel file found, starting with empty website list")


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
    start_time = time.time()

    # Resolve IP address if not already done
    if not websites[url].get("ip") or websites[url]["ip"] == "Unknown":
        websites[url]["ip"] = get_website_ip(url)

    # Check SSL certificate for HTTPS sites
    ssl_info = None
    if url.startswith('https://'):
        try:
            ssl_info = SSLMonitor.check_ssl_certificate(url)
            websites[url]["ssl_info"] = ssl_info
            logging.info(
                f"SSL check for {url}: Grade {ssl_info.get('grade', 'Unknown')}")
        except Exception as e:
            logging.error(f"SSL check failed for {url}: {e}")
            websites[url]["ssl_info"] = {
                'valid': False, 'error': str(e), 'grade': 'F'}

    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.get(url, timeout=30)
            # Convert to milliseconds
            response_time = round((time.time() - start_time) * 1000, 2)

            websites[url]["status_code"] = response.status_code
            websites[url]["response_time"] = f"{response_time}ms"
            websites[url]["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")

            if response.status_code == 200:
                websites[url]["status"] = "UP"
                websites[url]["error_count"] = 0  # Reset error count
                websites[url]["last_error"] = None  # Clear any previous error

                # Calculate enhanced health score for successful check
                try:
                    current_data = {
                        'url': url,
                        'status': websites[url]["status"],
                        'status_code': websites[url].get("status_code"),
                        'response_time': websites[url].get("response_time"),
                        'error_count': websites[url].get("error_count", 0),
                        'ssl_info': websites[url].get("ssl_info", {})
                    }

                    # Add to performance history
                    add_performance_record(url, current_data)

                    # Calculate enhanced health score
                    health_data = calculate_enhanced_health_score(
                        url, current_data)
                    websites[url]["health_score"] = health_data

                except Exception as e:
                    logging.error(
                        f"Error calculating enhanced health score for {url}: {e}")
                    websites[url]["health_score"] = {
                        'score': 0, 'grade': 'F', 'status': 'ERROR'}

                logging.info(
                    f"Website is available: {url} ({response_time}ms)")
                return True
            else:
                error_msg = f"HTTP {response.status_code}"
                websites[url]["last_error"] = error_msg
                logging.warning(
                    f"Warning: {url} returned status code {response.status_code}")

        except requests.exceptions.ConnectTimeout as e:
            error_msg = f"Connection timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(f"Timeout: {url} connection timeout. Exception: {e}")
        except requests.exceptions.ReadTimeout as e:
            error_msg = f"Read timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(f"Timeout: {url} read timeout. Exception: {e}")
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection failed: {str(e)[:100]}"
            websites[url]["last_error"] = error_msg
            logging.error(f"Error: {url} is not reachable. Exception: {e}")
        except requests.exceptions.Timeout as e:
            error_msg = f"Request timeout after 30s"
            websites[url]["last_error"] = error_msg
            logging.error(
                f"Timeout: {url} took too long to respond. Exception: {e}")
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)[:100]}"
            websites[url]["last_error"] = error_msg
            logging.error(f"Unexpected error checking {url}: {e}")

    # If we get here, all attempts failed
    websites[url]["error_count"] += 1
    websites[url]["last_check"] = time.strftime("%Y-%m-%d %H:%M:%S")

    if websites[url]["error_count"] >= ERROR_THRESHOLD:
        websites[url]["status"] = "DOWN"
        # send_email_alert(url)  # Uncomment if you want email alerts
    else:
        websites[url]["status"] = "SLOW"

    logging.error(f"Website {url} failed all {RETRY_COUNT + 1} attempts")

    # Calculate enhanced health score after check completes
    try:
        current_data = {
            'url': url,
            'status': websites[url]["status"],
            'status_code': websites[url].get("status_code"),
            'response_time': websites[url].get("response_time"),
            'error_count': websites[url].get("error_count", 0),
            'ssl_info': websites[url].get("ssl_info", {})
        }

        # Add to performance history
        add_performance_record(url, current_data)

        # Calculate enhanced health score
        health_data = calculate_enhanced_health_score(url, current_data)
        websites[url]["health_score"] = health_data

    except Exception as e:
        logging.error(
            f"Error calculating enhanced health score for {url}: {e}")
        websites[url]["health_score"] = {
            'score': 0, 'grade': 'F', 'status': 'ERROR'}
    except Exception as e:
        logging.error(f"Error calculating health score for {url}: {e}")
        websites[url]["health_score"] = {
            'score': 0, 'grade': 'F', 'status': 'ERROR'}

    return False

    logging.error(
        f"{url} has been down for {websites[url]['error_count']} consecutive checks")
    return False


def check_websites():
    """Check all websites in the global websites dictionary"""
    if not websites:
        logging.info("No websites to check")
        return

    logging.info(f"Starting check for {len(websites)} websites")

    threads = []
    # Create a copy of keys to avoid modification during iteration
    for website in list(websites.keys()):
        web_thread = Thread(target=check_website, args=(website,))
        web_thread.start()
        threads.append(web_thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    logging.info("Completed checking all websites")


def periodic_monitoring(interval=3600):  # 1 hour by default
    while True:
        check_websites()
        time.sleep(interval)
